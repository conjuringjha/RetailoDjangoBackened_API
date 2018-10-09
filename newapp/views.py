from django.shortcuts import render
# Create your views here.
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from django.contrib.auth.decorators import permission_required,login_required
import google.cloud.storage
import uuid
import psycopg2
from psycopg2 import sql
import json
import re
import datetime
import time
import geocoder
from datetime import timedelta


############################################################################################################################################################################3
#Establishing conection with Database
conn = psycopg2.connect("dbname=postgres user=postgres password=fortuner123 host='35.224.223.126'")
cur = conn.cursor()

#to get back photos from database with appropriate filters applied
def filtered_photos(Brand=None, levelofidentification=None, result=None, auth_id=None, outlet_id=None, region=None, date_1 = (datetime.date.today()-timedelta(45)),date_2 = datetime.date.today()):

    cur.execute("""SELECT * FROM image_data WHERE Brand = COALESCE(%s,Brand) 
        AND levelofidentification=COALESCE(%s,levelofidentification)
        AND Result = COALESCE(%s,Result) 
        AND auth_id = COALESCE(%s,auth_id)
        AND outlet_id = COALESCE(%s,outlet_id)
        AND region = COALESCE(%s,region)
        AND date >= %s
        AND date <=%s ORDER BY timestamp""", (Brand, levelofidentification, result, str(auth_id), outlet_id, region, date_1, date_2))

    records = cur.fetchall()
    return (records)

#to get nearby locations from database depending on current location using geo-coordinates
def nearby_me(lat, long, cat, auth_id):
    statement = 'SRID=4326;POINT(' + str(lat) + ' ' + str(long) + ')'
    print(statement)

    GEOLOCATION_API_KEY = 'AIzaSyATsf_49alc-rwyQ9rin_GDZ2cQHYdBUU8'
    latitude = float(lat)
    longitude = float(long)
    location = geocoder.google([latitude, longitude], method='reverse', key='AIzaSyATsf_49alc-rwyQ9rin_GDZ2cQHYdBUU8')
    loc_data = location.address.split(',')
    print(location.address)
    l = len(loc_data)
    state = loc_data[l - 2].split()[0]  ##State
    city = loc_data[l - 3]  ##City
    area = loc_data[l - 4]
    area_list = []
    area_list.append(area)
##AND city = %s
    cur.execute("""SELECT brand, store_name FROM storelocation2 WHERE ST_DWithin(gps_pos, ST_GeogFromText(%s), 50000)
                 AND user_id = %s AND category = %s""",
                (statement, str(auth_id), cat))
    records = cur.fetchall()
    outlets = []
    brandjson = dict({})
    for record in records:
        if record[1] not in outlets:
            outlets.append(record[1])
            brandjson[record[1]] = []
        brandjson[record[1]].append(record[0])

    outlets_records = {'brands':brandjson, 'outlets':outlets,'area':area_list, 'city':city,'state':state}
    print(outlets_records)
    outlets_list = {'outlets_list':outlets_records}
    outlets_list = json.dumps(outlets_list)
    return outlets_list


#to get list of regions from database for the stacked graph(region-number-result)
def x_axis_points():
    cur.execute("SELECT region FROM image_data")
    raw_records = list(set(cur.fetchall()))
    records = []
    for r in raw_records:
        records.append(r[0])
    return (records)

#to get list of brands from databse for the stacked graph(brand-number-result)
def x_axis_brands(id):
    cur.execute("SELECT brand FROM image_data WHERE auth_id = %s" , (str(id)))
    raw_records = list(set(cur.fetchall()))
    records = []
    for r in raw_records:
        records.append(r[0])
    return (records)

#to get number of records for each region for the stacked graph(region-number-result)
def records_number_region(region=None, brand=None, result=None, auth_id=None ,date_1 = datetime.date.today() , date_2 = datetime.date.today() ):
    print(auth_id)
    cur.execute(
        """SELECT COUNT(*) FROM image_data WHERE auth_id = COALESCE(%s,auth_id) AND brand=COALESCE(%s,brand) AND result = COALESCE(%s,result) AND region = COALESCE(%s,region) 
        AND date >= %s AND date <=  %s""",
        (str(auth_id), brand, result, region, date_2 , date_1))

    records = cur.fetchall()
    return (records[0][0])

#to compile the data required to plot the stacked graph
def stacked_chart(chart='brand', a_id=None , d_1 = datetime.date.today() , d_2 = datetime.date.today()):
    print(d_1)
    print(d_2)
    if (chart == 'brand'):
        x_brands = x_axis_brands(a_id)
        x_pass = []
        x_fail = []
        for x in x_brands:
            x_pass.append(records_number_region(brand=x, result='pass', auth_id=a_id , date_1=d_1 , date_2=d_2 ))
            x_fail.append(records_number_region(brand=x, result='fail', auth_id=a_id , date_1=d_1 , date_2=d_2 ))

        result = {"x_axis": x_brands, "pass": x_pass, "fail": x_fail}
        return (result)

    elif (chart == 'region'):
        x_locations = x_axis_points()
        x_pass = []
        x_fail = []
        for x in x_locations:
            x_pass.append(records_number_region(region=x, result='pass', auth_id=a_id, date_1=d_1 , date_2=d_2))
            x_fail.append(records_number_region(region=x, result='fail', auth_id=a_id, date_1=d_1 , date_2=d_2))

        result = {"x_axis": x_locations, "pass": x_pass, "fail": x_fail}
        return (result)


#************************************************************************************WEB APPLICATION***************************************************************************

#to send data to the webapp that can be displayed in the dropdown of the filter - brands
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def dropdown_webapp_brands(request,query=None):
    user = request.user.id
    cur.execute ("""SELECT * FROM image_data WHERE auth_id = %s""" , (str(user) , ))
    records = cur.fetchall()
    Brands = []
    labels = []
    for r in records:
        labels.append(r[1])
    labels = list(set(labels))
    print(labels)
    for l in labels:
        sample = {"brand": ""}
        sample["brand"] = l
        print(l)
        print(sample)
        print(Brands)
        Brands.append(sample)
    dropdown_data =  Brands
    print(dropdown_data)
    return Response(dropdown_data)

#to send data to the webapp that can be displayed in the dropdown of the filter - region
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def dropdown_webapp_region(request,query=None):
    user = request.user.id
    cur.execute ("""SELECT * FROM image_data WHERE auth_id = %s""" , (str(user) , ))
    records = cur.fetchall()
    Regions = []
    labels = []
    #Dates = []
    for r in records:
        labels.append(r[9])
    labels = list(set(labels))
    for l in labels:
        #print(r)
        sample = {"region" : ""}
        sample["region"] = l
        Regions.append(sample)

    dropdown_data = Regions

    return Response(dropdown_data)

#to send data to the webapp that can be displayed in the dropdown of the filter - locality
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def dropdown_webapp_locality(request,query=None):
    user = request.user.id
    cur.execute ("""SELECT * FROM image_data WHERE auth_id = %s""" , (str(user) , ))
    records = cur.fetchall()
    Outlet_ids = []
    location = []
    for r in records:
        location.append(r[10])
    location = list(set(location))
    for l in location:
        #print(r)
        sample = {"location" : ""}
        sample["location"] = l
        Outlet_ids.append(sample)

    dropdown_data =  Outlet_ids
    return Response(dropdown_data)

#to send data to the webapp that can be displayed in the dropdown of the filter - user_id
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def dropdown_webapp_userid(request,query=None):
    user = request.user.id
    print(user)
    cur.execute ("""SELECT * FROM image_data WHERE auth_id = %s""" , (str(user) , ))
    records = cur.fetchall()
    User_ids = []
    users = []

    for r in records:
        users.append(r[12])
    users = list(set(users))

    for u in users:
        sample = {"userid" : ""}
        sample["userid"] = u
        User_ids.append(sample)
    dropdown_data =  User_ids
    return Response(dropdown_data)

#to return images to the webapp user on the basis of filters selected
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def image_urls(request,query=None):
    print("GET data : " , request.GET)
    auth_id = request.user.id
    print(auth_id)
    start = (request.GET.get('start',1))

    #######################################################################################
    testing_region = request.GET.get('region' , None)
    print(testing_region)
    if (not (testing_region == None)):
        testing_region = re.sub("\[" , '' , testing_region)
        testing_region = re.sub("\]", '', testing_region)
        print(testing_region)
        if not(testing_region == 'null' or len(testing_region )== 0):
            testing_region = testing_region.split(',')
            print("list : " , testing_region)
            for i in range(0,len(testing_region)):
                testing_region[i] = json.loads(testing_region[i])
            print("tesing : " , testing_region[0]["region"])
            region = testing_region[0]["region"]
        else:
            region = None

    else:
        region = None
    ########################################################################################

    testing_region = request.GET.get('brands' , None)
    if (not(testing_region == None )):
        print(testing_region[0])
        testing_region = re.sub("\[" , '' , testing_region)
        testing_region = re.sub("\]", '', testing_region)
        print(testing_region)
        #testing_region = list(testing_region)
        testing_region = testing_region.split(',')
        print("list : " , testing_region[0])
        if not(testing_region[0] == 'null' or len(testing_region[0] )== 0):

            for i in range(0,len(testing_region)):
                testing_region[i] = json.loads(testing_region[i])
            print("tesing : " , testing_region[0]["brand"])
            brand = testing_region[0]["brand"]
        else:
            brand = None
    else:
        brand = None
    ########################################################################################

    testing_region = request.GET.get('result' , None)
    print(testing_region)
    if (not (testing_region == None)):
        testing_region = re.sub("\[" , '' , testing_region)
        testing_region = re.sub("\]", '', testing_region)
        print(testing_region)
    #testing_region = list(testing_region)
        testing_region = testing_region.split(',')
        print("list : " , testing_region)
        if not (testing_region[0] == 'null' or len(testing_region[0] )== 0):
            for i in range(0,len(testing_region)):
                testing_region[i] = json.loads(testing_region[i])
            print("tesing : " , testing_region[0]["result"])
            result = testing_region[0]["result"]
        else:
            result = None
    else:
        result = None
    ########################################################################################
    testing_region = request.GET.get('outlet_id')
    print(testing_region)
    if (not (testing_region == None)):
        testing_region = re.sub("\[" , '' , testing_region)
        testing_region = re.sub("\]", '', testing_region)
        print(testing_region)
        testing_region = testing_region.split(',')
        print("list : " , testing_region[0])
        if not (testing_region[0] == 'null' or len(testing_region[0] )== 0):
            for i in range(0,len(testing_region)):
                testing_region[i] = json.loads(testing_region[i])
            print("tesing : " , testing_region[0]["location"])
            outlet_id = testing_region[0]["location"]
        else:
            outlet_id = None
    else:
        outlet_id = None
    ########################################################################################

    testing_region = request.GET.get('u_id')
    print(testing_region)
    if (not (testing_region == None)):
        testing_region = re.sub("\[", '', testing_region)
        testing_region = re.sub("\]", '', testing_region)
        print(testing_region)
        testing_region = testing_region.split(',')
        print("list : ", testing_region[0])
        if not (testing_region[0] == 'null' or len(testing_region[0]) == 0):
            for i in range(0, len(testing_region)):
                testing_region[i] = json.loads(testing_region[i])
            print("tesing : ", testing_region[0]["userid"])
            outlet_id = testing_region[0]["userid"]
        else:
            outlet_id = None
    else:
        outlet_id = None
    ########################################################################################
    #date
    testing_region = request.GET.get('startdate')
    if not(testing_region == 'Select Start Date'):
        date_1 = testing_region
    else:
        date_1 = datetime.date.today() - timedelta(45)
    print(date_1)
##############################################################
    testing_region = request.GET.get('enddate')
    if not(testing_region == 'Select End Date'):
        date_2 = testing_region
    else:
        date_2 = datetime.date.today()
    print(date_2)

    ########################################################################################
    start = int(start)
    end = int(start+9)
    links = []

    loi = request.GET.get("loi" , None)
    #u_id = request.GET.get("u_id" , None)

    records = filtered_photos(brand , loi , result , auth_id , outlet_id , region,date_1, date_2 )
    print(len(records))
    for i in range(0,len(records)):
        links.append(records[i])

    result = {"links" : links[start:end]}
    print("number of photos : " , len(result["links"]))
    return Response(result)

#to return chart data depending on type of chart
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def charts_brand(request ):
    user = request.user.id
    ####################################################################################################################
    chart_type = request.GET.get('chart_type', None)
    time_period = request.GET.get('time_period' , None)

    print(chart_type , time_period)
    date_1 = datetime.date.today()
    date_2 = datetime.date.today()

    if (time_period == 'today' or time_period == None):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today()

    elif(time_period == 'this week'):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() - timedelta(7)

    elif(time_period == 'this month'):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() - timedelta(30)

    print(date_1 , ' ', date_2)
    result = stacked_chart(chart_type, user, date_1, date_2)
    print(result)

    list_1 = []
    list_2 = []

    for i in range(len(result["x_axis"])):
        sample = {"x": "", "y":0}
        sample["x"] = result["x_axis"][i]
        if not((int(result["pass"][i]) + int(result["fail"][i])) == 0):
            sample["y"] = int((((int(result["pass"][i])/(int(result["pass"][i]) + int(result["fail"][i])))*100)))
        else:
            sample["y"] = 0
        list_1.append(sample)

    for i in range(len(result["x_axis"])):
        sample = {"x": "", "y": 0}
        sample["x"] = result["x_axis"][i]

        if not ((int(result["pass"][i]) + int(result["fail"][i])) == 0):
            sample["y"] = (((int(result["fail"][i])/(int(result["pass"][i]) + int(result["fail"][i])))*100))
        else:
            sample["y"] = 0
        list_2.append(sample)

    return Response({"pass" : list_1 , "fail" : list_2})

@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def charts_region(request ):
    user = request.user.id
    ####################################################################################################################
    chart_type = request.GET.get('chart_type', None)
    time_period = request.GET.get('time_period' , None)

    print(chart_type , time_period)
    date_1 = datetime.date.today()
    date_2 = datetime.date.today()

    if (time_period == 'today' or time_period == None):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today()

    elif(time_period == 'this week'):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() - timedelta(7)

    elif(time_period == 'this month'):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() - timedelta(30)

    print(date_1 , ' ', date_2)
    result = stacked_chart(chart_type, user, date_1, date_2)
    print(result)

    list_1 = []
    list_2 = []

    for i in range(len(result["x_axis"])):
        sample = {"x": "", "y": 0}
        sample["x"] = result["x_axis"][i]
        if not((int(result["pass"][i]) + int(result["fail"][i])) == 0):
            sample["y"] = (((int(result["pass"][i])/(int(result["pass"][i]) + int(result["fail"][i])))*100))
        else:
            sample["y"] = 0
        list_1.append(sample)

    for i in range(len(result["x_axis"])):
        sample = {"x": "", "y": 0}
        sample["x"] = result["x_axis"][i]

        if not ((int(result["pass"][i]) + int(result["fail"][i])) == 0):
            sample["y"] = (((int(result["fail"][i])/(int(result["pass"][i]) + int(result["fail"][i])))*100))
        else:
            sample["y"] = 0
        list_2.append(sample)

    return Response({"pass" : list_1 , "fail" : list_2})


@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def total_number(request):
    user = request.user.id
    time_period = request.GET.get('time_period', None)
    d_1 = datetime.date.today()
    d_2 = datetime.date.today()

    if (time_period == 'today' or time_period == None):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today()

    elif (time_period == 'this week'):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today() - timedelta(7)

    elif (time_period == 'this month'):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today() - timedelta(30)

    print(d_1, ' ', d_2)
    result = records_number_region(auth_id = user , date_1 = d_1, date_2 = d_2)
    return Response( {'TotalRecords' : result})

@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def pie_chart(request):
    user = request.user.id
    time_period = request.GET.get('time_period', None)
    d_1 = datetime.date.today()
    d_2 = datetime.date.today()

    if (time_period == 'today' or time_period == None):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today()

    elif (time_period == 'this week'):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today() - timedelta(7)

    elif (time_period == 'this month'):
        d_1 = datetime.date.today()
        d_2 = datetime.date.today() - timedelta(30)
    total_pass = records_number_region(auth_id=user , result='pass' , date_1 = d_1, date_2 = d_2)
    total_fail = records_number_region(auth_id=user , result= 'fail' , date_1 = d_1, date_2 = d_2)
    print(total_fail , ' ' , total_pass)
    return Response({"pass" : total_pass , "fail" : total_fail})
#*************************************************************************************MOBILE APPLICATON API*********************************************************************************************8

######to return current address using latitude and longitude using geocoder and List of brands
@api_view(['POST'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def return_address(request):
    GEOLOCATION_API_KEY = 'AIzaSyATsf_49alc-rwyQ9rin_GDZ2cQHYdBUU8'
    lat = float(request.data["latitude"])
    long = float(request.data["longitude"])
    location = geocoder.google([lat,long], method='reverse',key='AIzaSyATsf_49alc-rwyQ9rin_GDZ2cQHYdBUU8')
    loc_data = location.address.split(',')
    print(loc_data)

    l = len(loc_data)
    state = loc_data[l-2].split()[0]  ##State
    pin = loc_data[l-2].split()[1]   ##Pincode
    city = loc_data[l-3]          ##City
    area = loc_data[l-4]          #Area

    cur.execute("""SELECT * FROM brands""")
    records = cur.fetchall()
    Outlet_ids = []
    brands = []
    cat = []
    for r in records:
        brands.append([r[1], r[2]])
        if r[2] not in cat:
            cat.append(r[2])

    result = {'area':area, 'city':city, 'state':state, 'pincode':pin, 'brands':brands, 'category':cat}
    print(result)
    loc_data = {'loc_data':result}
    loc_data = json.dumps(loc_data)
    return Response(loc_data)



######ADD OUTLET: to updte Outlet table List with NEW OUTLET with all details
@api_view(['POST'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def add_NewOutlet(request,):
    if request.method == 'POST':
        print(request.data)

        auth_id = request.user.id + 100
        lat = request.data['Latitude']
        long = request.data['Longitude']
        shopno = request.data["ShopNo"]
        outletname = request.data["OutletName"]
        brand = request.data["BrandName"]
        area = request.data['Area']
        city = request.data['City']
        state = request.data['State']
        pincode = request.data['Pincode']
        cat = request.data['Category']
        status_id = 0
        status = ''
        cur.execute("""SELECT store_id FROM storelocation2""")
        records = cur.fetchall()
        l = len(records)
        if l == 0:
            store_id = 1001
        else:
            store_id = 1 + records[l-1][0]

        statement = 'SRID=4326;POINT(' + str(lat) + ' ' + str(long) + ')'

        try:
            cur.execute(
                """INSERT INTO storelocation2(user_id,store_id,store_name,brand,store_shopno,area,city,state,pincode,gps_pos,category)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_GeogFromText(%s),%s)""",
                (str(auth_id), store_id,outletname,brand,shopno,area,city,state,str(pincode),statement,cat))
            conn.commit()
            status_id = 1
            status = "SUCCESS"
        except Exception as e:
            status_id = 0
            print(e)
            status = "DB Entry Failure."

        print(status)
        return Response(status)
    else:
        return Response("Post Request Not Sent")

#to return nearby outlets to the mobile app depending upon location-coordinates of the user
@api_view(['POST'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def location(request, ):
    auth_id = request.user.id + 100
    data = {"latitude": request.data["latitude"], "longitude": request.data["longitude"]}
    lat = request.data["latitude"]
    long = request.data["longitude"]
    cat = request.data["cat"]
    outlets_records = nearby_me(lat,long, cat, auth_id)
    return Response(outlets_records)

@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def getData(request, ):
    auth_id = request.user.id + 100
    cur.execute("Select store_name from storelocation")
    records = cur.fetchall()
    resp = {'data':records}
    resp = json.dumps(resp)
    return Response(resp)


#to get the image and text data from the mobile app,
#upload the image to the google cloud storage,
#save the url of uploaded image and dump the details along with the url to the image_data table
@api_view(['POST'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def boardImage_upload(request):
    if request.method == 'POST':
        print("entered board upload function")
        print("data : " , request.data)
        print("Name : " , request.data["Name"])
        print("Location" , request.data["Location"])
        print("Outletname" , request.data["OutletName"])

        auth_id = request.user.id

        request._load_post_and_files()

        uploaded_file = request.FILES.get('image')
        print(uploaded_file)
        storage_client = google.cloud.storage.Client()
        bucket_name = 'user_image_123'
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(uploaded_file.name)
        blob.upload_from_string(uploaded_file.read(), content_type=uploaded_file.content_type)

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(st)

        #when uploading files from system to generqate test data, uncomment the following lines so aa to form a realistic database
        '''loi = request.FILES.get('loi')
        data_2 = loi.read()
        print(str(loi))
        LOI = data_2.decode('utf-8')'''

        '''u_id = request.FILES.get('u_id')
        data_4 = u_id.read()
        print(str(u_id))
        U_ID = data_4.decode('utf-8')'''

        '''result = request.FILES.get('result')
        data_5 = result.read()
        print(str(result))
        RESULT = data_5.decode('utf-8')'''

        UNIQUEUE_ID = str(uuid.uuid4())
        db_name = str(UNIQUEUE_ID) + ".jpeg"
        print(db_name)

        cur.execute("INSERT INTO image_data(image_db_id,brand ,status  ,imageurl ,imagenewurl ,auth_id ,Region ,Outlet_id,db_name,timestamp   ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (UNIQUEUE_ID,request.data["Name"], "UNPROCESSED",blob.public_url,blob.public_url,auth_id,request.data["Location"],request.data["OutletName"],db_name ,st ))

        conn.commit()

        return Response('GOT A POST REQUEST')
    else:
        return Response('POST REQUEST NOT RECEIVED')


#to get the image and text data from the mobile app,
#upload the image to the google cloud storage,
#save the url of uploaded image and dump the details along with the url to the image_data table
@api_view(['POST'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def shelfImage_upload(request):
    if request.method == 'POST':
        print("entered upload function")
        print("data : " , request.data)
        print("Brand Name : " , request.data["BrandName"])
        print("Location" , request.data["Location"])
        print("Outletname" , request.data["OutletName"])


        auth_id = request.user.id

        request._load_post_and_files()

        uploaded_file = request.FILES.get('image')
        print(uploaded_file)
        storage_client = google.cloud.storage.Client()
        bucket_name = 'shelf_images'
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob("unprocessed/"+uploaded_file.name)
        blob.upload_from_string(uploaded_file.read(), content_type=uploaded_file.content_type)

        #Generating GPS position
        lat = request.data['lat']
        long = request.data['long']
        gps_string = 'SRID=4326;POINT(' + str(lat) + ' ' + str(long) + ')'

        #Generating current time
        ts = time.time()
        clicktime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(clicktime)

        #when uploading files from system to generqate test data, uncomment the following lines so aa to form a realistic database
        '''loi = request.FILES.get('loi')
        data_2 = loi.read()
        print(str(loi))
        LOI = data_2.decode('utf-8')'''

        '''u_id = request.FILES.get('u_id')
        data_4 = u_id.read()
        print(str(u_id))
        U_ID = data_4.decode('utf-8')'''

        '''result = request.FILES.get('result')
        data_5 = result.read()
        print(str(result))
        RESULT = data_5.decode('utf-8')'''

        UNIQUEUE_ID = str(uuid.uuid4())
        db_name = str(UNIQUEUE_ID) + ".jpg"
        print(db_name)

        storename = request.data["OutletName"]
        cat = request.data["Category"]
        print()

        try:
            #Getting store id
            cur.execute("Select store_id from storelocation2 WHERE category = %s AND store_name = %s", (cat, storename))
            store_id = cur.fetchone()

            cur.execute("""INSERT INTO image_data_shelf(image_id, store_id, image_dblink, user_id, gps_pos, clicktime, status)
                         VALUES (%s,%s,%s,%s,ST_GeogFromText(%s),%s,%s)""",
                        (UNIQUEUE_ID,store_id,blob.public_url, auth_id, gps_string, clicktime,"UNPROCESSED"))

            conn.commit()
            resp = "Store Updated Successfully!"
        except Exception as e:
            resp = str(e)

        return Response(resp)
    else:
        return Response('POST REQUEST NOT RECEIVED')



#to return Processed Shelf images uploaded by the mobile app user
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def load_shelf_images(request,query=None):
    auth_id = request.user.id
    links = []
    cur.execute("""SELECT * FROM image_data_shelf WHERE user_id = %s ORDER BY clicktime""" , (str(auth_id),))
    records = cur.fetchall()
    print(records)
    for i in range(0,len(records)):
        sample = {"imageurl" : "" , "image_id" : "" , "store_id" : "", "store_name" : "", "status":""}
        sample["imageurl"] = records[i][2]
        sample["image_id"] = records[i][0]
        sample["store_id"] = records[i][1]
        cur.execute("Select store_name, area from storelocation2 WHERE category = %s AND store_id = %s", ("Shelf", sample["store_id"]))
        rec = cur.fetchone()
        sample["store_name"] = rec[0]
        sample["area"] = rec[1]
        sample["status"] = records[i][6]

        # sample["brand"] = records[i][1]
        # sample["result"] = records[i][11]
        # sample["region"] = records[i][9]
        # sample["loi"] = records[i][5]
        links.append(sample)

    result = {"links" : links}
    result = json.dumps(result)
    return Response(result)

#to return processed Board images uploaded by the mobile app user
@api_view(['GET'])
@authentication_classes((SessionAuthentication, TokenAuthentication, BasicAuthentication))
@permission_classes((IsAuthenticated,))
def load_board_images(request,query=None):
    auth_id = request.user.id
    links = []
    cur.execute("""SELECT * FROM image_data WHERE auth_id = %s ORDER BY timestamp""" , (str(auth_id),))
    records = cur.fetchall()
    print(records)
    for i in range(0,len(records)):
        sample = {"imageurl" : "" , "brand" : "" , "result" : "" , "region" : "" , "loi" : "" , "status" : "","outlet_name" : ""}
        sample["imageurl"] = records[i][7]
        sample["brand"] = records[i][1]
        sample["result"] = records[i][11]
        sample["region"] = records[i][9]
        sample["loi"] = records[i][5]
        sample["status"] = records[i][2]
        sample["outlet_name"] = records[i][10]
        links.append(sample)

    result = {"links" : links}
    result = json.dumps(result)
    return Response(result)
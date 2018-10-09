from django.shortcuts import render

# Create your views here.
from rest_framework.parsers import JSONParser,MultiPartParser,FormParser
from rest_framework.renderers import JSONRenderer

#import rest_framework.parsers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.serializers import UserSerializer
from accounts.serializers import AuthCustomTokenSerializer
from rest_framework.authtoken.models import Token
import json
import psycopg2
from django.contrib.auth.models import User
conn = psycopg2.connect("dbname=postgres user=postgres password=fortuner123 host='35.224.223.126'")
cur = conn.cursor()

class UserCreate(APIView):
    """
    Creates the user.
    """
    def post(self, request, format='json'):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if user:
                token = Token.objects.create(user=user)
                json = serializer.data
                json['token'] = token.key
                return Response(json, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (
        FormParser,
        MultiPartParser,
        JSONParser,
    )

    renderer_classes = (JSONRenderer,)

    def post(self, request):
        #print("request data is" , request.data)
        #print(request.data["_parts"][0][1])
        #print("request body is" , request.body)

        if not("source" in request.data):
            serializer = AuthCustomTokenSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']

            if(user.is_superuser):
                role = "admin"
            else:
                role = "manager"
            token, created = Token.objects.get_or_create(user=user)
            print(token.user_id)
            cur.execute("SELECT user_name,company_name FROM image_data WHERE auth_id = %s" , (str(token.user_id)))
            records = list(set(cur.fetchall()))
            print(records)
            content = {
                'status' : 'success','role' : role,'token': str(token.key) , 'user_name' : records[0][0] , 'company_name' : records[0][1]
            }
        #print(content)
            return Response(content)
        else:
            #parts = request.data["_parts"]

            mock_data = {"email_or_username" : request.data["email_or_username"] , "password" : request.data["password"] }

            serializer = AuthCustomTokenSerializer(data=mock_data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            if (user.is_superuser):
                role = "admin"
            else:
                role = "manager"
            token, created = Token.objects.get_or_create(user=user)

            content = {
                "status": "success", "role": role, "token": str(token.key)
            }
            content = json.dumps(content)
            # print(content)
            return Response(content)
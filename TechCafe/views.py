# views.py
import requests
from django.http import JsonResponse
from rest_framework.views import APIView
from .mongo_client import users
import jwt, datetime
from decouple import config
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime, timedelta, timezone


@api_view(["POST"])
def GitHubAuthView(request):
        code = request.data.get('code')
        token_url = "https://github.com/login/oauth/access_token"
        token_response = requests.post(token_url, data={
            "client_id": config("GITHUB_CLIENT_ID"),
            "client_secret": config("GITHUB_CLIENT_SECRET"),
            "code": code
        }, headers={"Accept": "application/json"})

        token_json = token_response.json()
        access_token = token_json.get("access_token")

        user_info = requests.get("https://api.github.com/user", headers={
            "Authorization": f"token {access_token}"
        }).json()
        print(user_info)
        github_id = user_info.get("id")
        email = user_info.get("email")
        name = user_info.get("login")
        avatar = user_info.get("avatar_url")

        user = users.find_one({"github_id": github_id})
        if not user:
            users.insert_one({
                "github_id": github_id,
                "name": name,
                "email": email,
                "avatar": avatar
            })

        payload = {
            "github_id": github_id,
           "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        jwt_token = jwt.encode(payload, config("JWT_SECRET"), algorithm="HS256")

        return JsonResponse({"token": jwt_token, "user": {"name": name, "avatar": avatar}})


# meet/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from fastapi_app.queue.queue import enqueue_user, get_queue_length, dequeue_users
import json
import traceback
@api_view(["POST"])
def join_queue_view(request):
        try:
            print("Request received:", request.body)
            data = json.loads(request.body)
            print(data)
            user_id = data["user_id"]
            domain=data["domain"]

            result = enqueue_user( domain,user_id)
            return JsonResponse(result, status=200, safe=False)

        except Exception as e:
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=400)

@api_view(["GET"])
def queue_status_view(request):
        try:
            domain = request.GET.get("domain")
            room_type = request.GET.get("room_type")

            result = get_queue_length(domain, room_type)
            return JsonResponse(result, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@api_view(["GET"])
def simulate_room_view(request):
        try:
            domain = request.GET.get("domain")
            room_type = request.GET.get("room_type")

            users = dequeue_users(domain, room_type)
            return JsonResponse(users, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


from flask import Flask, jsonify, request, json
from prometheus_flask_exporter import PrometheusMetrics
import pymongo
import os
from pymongo import MongoClient

server_port = os.environ.get("SERVER_PORT")
db_port = os.environ.get("DB_PORT")
db_username = os.environ.get("DB_USERNAME")
db_password = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")
app = Flask(__name__)
metrics = PrometheusMetrics(app)
MONGO_URI = (
    f"mongodb://{db_username}:{db_password}@{host}:{db_port}/allUsers?authSource=admin"
)
client = MongoClient(MONGO_URI)

db = client.allUsers
query = db.users


@app.route("/")
def hello_world() -> tuple:
    return "Success", 200, {"Access-Control-Allow-Origin": "*"}


# Endpoint for checking user and return true or false to login handling
@app.route("/api/login", methods=["POST"])
def login_user() -> tuple:
    input = json.loads(request.data)
    test = input["username"]
    test2 = input["password"]
    data = []
    users = query.find(
        {"username": test, "password": test2},
        {"id": 1, "username": 1, "avatar": 1, "role": 1, "_id": 0},
    )
    for user in users:
        data.append(user)
    return data, 200, {"Access-Control-Allow-Origin": "*"}


# Endpoint for reading all users. Works?.
@app.route("/api/users", methods=["GET"])
def get_all_users() -> tuple:
    data = []
    users = query.find({}, {"password": 0, "email": 0, "name": 0, "_id": 0})
    for user in users:
        data.append(user)
    return jsonify(data)


@app.route("/api/product", methods=["POST"])
def post_products() -> tuple:
    data = json.loads(request.data)
    data["id"] = int(increment_post())
    query.insert_one(data)
    return "a new post has been added", 201, {"Access-Control-Allow-Origin": "*"}


# Endpoint for user creation. Works.
@app.route("/api/user", methods=["POST"])
def create_user() -> tuple:
    try:
        data_list = json.loads(request.data)
        if not data_list["username"] or not data_list["name"]:
            return jsonify({"message": "Username and/or name are required"}), 400
        if not data_list["password"] or not data_list["email"]:
            return jsonify({"message": "Password and/or email are required"}), 400
        if query.find_one({"password": data_list["password"]}):
            return jsonify({"message": "Password already exists"}), 400
        data_list["id"] = int(increment_post())
        # Insert the new user document into the 'users' collection
        query.insert_one(data_list)
        return (
            jsonify({"message": "User created successfully"}),
            201,
        )

    except Exception as e:
        return jsonify({"message": "An error occurred", "error": str(e)}), 500


# Endpoint for updating user information. Works.
@app.route("/api/user/<int:user_id>", methods=["PUT"])
def update_user(user_id: int) -> tuple:
    try:
        # Get the JSON data from the request
        data = request.get_json()

        # Check if the request contains a valid JSON object
        if not data or not isinstance(data, dict):
            return (
                jsonify({"message": "Invalid JSON data in the request"}),
                400,
            )  # 400 indicates a bad request

        # Get the updated name and email fields from the JSON data
        updated_name = data.get("name")
        updated_email = data.get("email")

        # Check if the user with the provided user_id exists
        user = query.find_one({"id": user_id})

        if not user:
            return (
                jsonify({"message": "User not found"}),
                404,
            )  # 404 indicates resource not found

        # Update the user's name and email if provided in the JSON data
        if updated_name is not None:
            user["name"] = updated_name
        if updated_email is not None:
            user["email"] = updated_email

        # Update the user document in the MongoDB collection
        query.update_one({"id": user_id}, {"$set": user})

        return (
            jsonify({"message": "User updated successfully"}),
            200,
        )  # 200 indicates success

    except Exception as e:
        return (
            jsonify({"message": "An error occurred", "error": str(e)}),
            500,
        )  # 500 indicates an internal server error


# Endpoint for reading a user. Works.
@app.route("/api/user/<user_id>", methods=["GET"])
def get_single_user(user_id: int) -> tuple:
    data = []
    todos = query.find(
        {"id": int(user_id)}, {"password": 0, "email": 0, "name": 0, "_id": 0}
    )
    for doc in todos:
        data.append(doc)
    return jsonify(data)


# Endpoint for user deletion. Works.
@app.route("/api/user/<user_id>", methods=["DELETE"])
def delete_single_user(user_id: int) -> tuple:
    try:
        # Ensure user_id is an integer
        user_id = int(user_id)

        # Check if the user with the provided user_id exists
        user = query.find_one({"id": user_id})
        if not user:
            return (
                jsonify({"message": "User not found"}),
                404,
            )  # 404 indicates resource not found

        # Delete the user document with the provided user_id
        query.delete_one({"id": user_id})

        return (
            jsonify({"message": "User deleted successfully"}),
            200,
        )  # 200 indicates success

    except ValueError:
        return (
            jsonify({"message": "Invalid user ID"}),
            400,
        )  # 400 indicates a bad request

    except Exception as e:
        return (
            jsonify({"message": "An error occurred", "error": str(e)}),
            500,
        )  # 500 indicates an internal server error


def increment_post() -> str:
    id_fetch = query.find_one(sort=[("id", pymongo.DESCENDING)])
    return str(id_fetch["id"] + 1)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=server_port, debug=False)

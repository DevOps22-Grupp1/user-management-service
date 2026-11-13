from flask import Flask, jsonify, request
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.security import check_password_hash, generate_password_hash
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

# Every account made here is a customer. Admin is not a stored role: the home page grants it
# through the magic-link login, so no admin password exists anywhere.
CUSTOMER = "customer"
# The fields a sign-up may set; anything else in the request is ignored
SIGNUP_FIELDS = ("username", "name", "password", "email", "avatar")
HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def migrate_users() -> None:
    """Idempotent, on every start: plaintext passwords become hashes, every role customer."""
    for user in query.find({"password": {"$type": "string"}}, {"password": 1}):
        if not user["password"].startswith(HASH_PREFIXES):
            query.update_one(
                {"_id": user["_id"]},
                {"$set": {"password": generate_password_hash(user["password"])}},
            )
    query.update_many({"role": {"$ne": CUSTOMER}}, {"$set": {"role": CUSTOMER}})


@app.route("/")
def hello_world() -> tuple:
    return "Success", 200, {"Access-Control-Allow-Origin": "*"}


# Checks a username and password; answers [user] on a match, [] otherwise
@app.route("/api/login", methods=["POST"])
def login_user() -> tuple:
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    # Strings only: a JSON object here ({"$ne": null}) would otherwise be a Mongo query
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify([]), 200
    user = query.find_one(
        {"username": username},
        {"id": 1, "username": 1, "avatar": 1, "role": 1, "password": 1, "_id": 0},
    )
    stored = user.get("password") if user else None
    # An account without a password (the public demo accounts) cannot log in
    if not isinstance(stored, str) or not stored.startswith(HASH_PREFIXES):
        return jsonify([]), 200
    if not check_password_hash(stored, password):
        return jsonify([]), 200
    del user["password"]
    return jsonify([user]), 200


# Endpoint for reading all users. Works?.
@app.route("/api/users", methods=["GET"])
def get_all_users() -> tuple:
    data = []
    users = query.find({}, {"password": 0, "email": 0, "name": 0, "_id": 0})
    for user in users:
        data.append(user)
    return jsonify(data)


# Endpoint for user creation (sign-up)
@app.route("/api/user", methods=["POST"])
def create_user() -> tuple:
    try:
        data = request.get_json(silent=True) or {}
        user = {field: data.get(field) for field in SIGNUP_FIELDS}
        if not all(isinstance(value, str) for value in user.values()):
            return jsonify({"message": "All fields must be text"}), 400
        if not user["username"] or not user["name"]:
            return jsonify({"message": "Username and/or name are required"}), 400
        if not user["password"] or not user["email"]:
            return jsonify({"message": "Password and/or email are required"}), 400
        if query.find_one({"username": user["username"]}):
            return jsonify({"message": "Username already exists"}), 400
        user["password"] = generate_password_hash(user["password"])
        user["role"] = CUSTOMER
        user["bought"] = []
        user["id"] = int(increment_post())
        # Insert the new user document into the 'users' collection
        query.insert_one(user)
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
    return str(id_fetch["id"] + 1 if id_fetch else 1)


if __name__ == "__main__":
    migrate_users()
    app.run(host="0.0.0.0", port=server_port, debug=False)

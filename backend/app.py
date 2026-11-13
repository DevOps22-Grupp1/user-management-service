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
# The fields the account page may change (PUT /api/user/<id>)
PROFILE_FIELDS = ("name", "email", "avatar")
HASH_PREFIXES = ("scrypt:", "pbkdf2:")


def is_demo(user: dict) -> bool:
    """The shared demo account: everyone uses it, so nobody may lock the others out of it."""
    return bool(os.environ.get("DEMO_USERNAME")) and user.get("username") == os.environ.get("DEMO_USERNAME")


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

        # Only these fields, and only as text; the password and role have their own rules
        updates = {
            field: data[field] for field in PROFILE_FIELDS if isinstance(data.get(field), str)
        }

        # Check if the user with the provided user_id exists
        user = query.find_one({"id": user_id})

        if not user:
            return (
                jsonify({"message": "User not found"}),
                404,
            )  # 404 indicates resource not found

        if updates:
            query.update_one({"id": user_id}, {"$set": updates})

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


# The account page: what a customer may see and change about themselves
@app.route("/api/user/<int:user_id>/profile", methods=["GET"])
def get_profile(user_id: int) -> tuple:
    user = query.find_one(
        {"id": user_id}, {"username": 1, "name": 1, "email": 1, "avatar": 1, "_id": 0}
    )
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify(user)


# Changes the password; the current one must be right. The shared demo account keeps its own.
@app.route("/api/user/<int:user_id>/password", methods=["POST"])
def change_password(user_id: int) -> tuple:
    data = request.get_json(silent=True) or {}
    current, new = data.get("current"), data.get("new")
    if not isinstance(current, str) or not isinstance(new, str) or not new:
        return jsonify({"message": "Current and new password are required"}), 400
    user = query.find_one({"id": user_id})
    if not user:
        return jsonify({"message": "User not found"}), 404
    if is_demo(user):
        return jsonify({"message": "The demo account's password cannot be changed"}), 403
    stored = user.get("password")
    if not isinstance(stored, str) or not stored.startswith(HASH_PREFIXES) or not check_password_hash(stored, current):
        return jsonify({"message": "Wrong password"}), 403
    query.update_one({"id": user_id}, {"$set": {"password": generate_password_hash(new)}})
    return jsonify({"message": "Password changed"}), 200


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
        if is_demo(user):
            return jsonify({"message": "The demo account cannot be deleted"}), 403

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


def ensure_demo_account() -> None:
    """A public customer account for visitors who only want to look (DEMO_USERNAME and
    DEMO_PASSWORD; both unset means none). On every start it gets that password back, so
    nobody can take the name over by signing up with it first."""
    username = os.environ.get("DEMO_USERNAME")
    password = os.environ.get("DEMO_PASSWORD")
    if not username or not password:
        return
    fields = {"password": generate_password_hash(password), "role": CUSTOMER}
    if query.find_one({"username": username}):
        query.update_one({"username": username}, {"$set": fields})
    else:
        query.insert_one({
            "id": int(increment_post()),
            "username": username,
            "name": "Demo customer",
            "email": "",
            "avatar": os.environ.get("DEMO_AVATAR", ""),
            "bought": [],
            **fields,
        })


if __name__ == "__main__":
    migrate_users()
    ensure_demo_account()
    app.run(host="0.0.0.0", port=server_port, debug=False)

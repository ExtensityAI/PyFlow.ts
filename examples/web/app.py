from flask import Flask, request, jsonify
from pyflow import extensity
from typing import Dict, List, Any

app = Flask(__name__)

@extensity
class UserManager:
    users: Dict[str, Dict[str, Any]] = {}

    def add_user(self, user_id: str, name: str, email: str) -> Dict[str, Any]:
        """Add a new user."""
        if user_id in self.users:
            raise ValueError(f"User with ID {user_id} already exists")

        user = {
            "id": user_id,
            "name": name,
            "email": email
        }

        self.users[user_id] = user
        return user

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get a user by ID."""
        if user_id not in self.users:
            raise ValueError(f"User with ID {user_id} not found")

        return self.users[user_id]

    def list_users(self) -> List[Dict[str, Any]]:
        """List all users."""
        return list(self.users.values())

    def update_user(self, user_id: str, name: str = None, email: str = None) -> Dict[str, Any]:
        """Update a user."""
        if user_id not in self.users:
            raise ValueError(f"User with ID {user_id} not found")

        user = self.users[user_id]

        if name is not None:
            user["name"] = name

        if email is not None:
            user["email"] = email

        return user

    def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        if user_id not in self.users:
            raise ValueError(f"User with ID {user_id} not found")

        del self.users[user_id]

user_manager = UserManager()

@app.route("/api/users", methods=["GET"])
def list_users():
    return jsonify(user_manager.list_users())

@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.json
    try:
        user = user_manager.add_user(data["id"], data["name"], data["email"])
        return jsonify(user), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/users/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        user = user_manager.get_user(user_id)
        return jsonify(user)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@app.route("/api/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    try:
        user = user_manager.update_user(user_id, data.get("name"), data.get("email"))
        return jsonify(user)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@app.route("/api/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        user_manager.delete_user(user_id)
        return "", 204
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

if __name__ == "__main__":
    # This allows PyFlow.ts to run alongside Flask
    import threading
    import pyflow

    # Start PyFlow.ts server in a background thread
    pyflow_thread = threading.Thread(target=pyflow.run, args=["--module", "__main__"])
    pyflow_thread.daemon = True
    pyflow_thread.start()

    # Start Flask in the main thread
    app.run(debug=True, port=5000)
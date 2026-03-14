from flask import Flask, jsonify, request

def create_api(data_manager):
    app = Flask(__name__)

    @app.route("/feed", methods=["GET"])
    def feed():
        filters = {
            "tag": request.args.get("tag"),
            "author": request.args.get("author"),
            "date": request.args.get("date")
        }
        papers = data_manager.get_papers(filters)
        return jsonify(papers)

    @app.route("/register_institute", methods=["POST"])
    def register_institute():
        data = request.json
        data_manager.add_institute(
            name=data["name"], author=data["author"], mission=data.get("mission", ""), tags=data.get("tags", "")
        )
        return jsonify({"status": "registered", "author": data["author"]})

    @app.route("/validate_institute", methods=["GET"])
    def validate_institute():
        author = request.args.get("author")
        is_valid = data_manager.validate_institute(author)
        return jsonify({"valid": is_valid})

    return app

import json
from flask import Flask, render_template, request, send_file
from pymongo import MongoClient
import io
import csv

app = Flask(__name__)
visit_counter = 0  # Simple in-memory visit counter

# ✅ Connect to MongoDB
client = MongoClient("mongodb+srv://bobbykumaar:bXXck9xw91fSedzt@consumercluster.nooechs.mongodb.net/?retryWrites=true&w=majority&appName=ConsumerCluster")
db = client["consumers_db"]
collection = db["consumers"]

@app.template_filter('pretty_key')
def pretty_key(key):
    return key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip()

def get_consumer_data(query_value, search_type):
    try:
        field = "consumer_number" if search_type == "consumer" else "new_meter_qr_code"
        query = {field: query_value}

        result = collection.find_one(query)

        # Retry without leading zeros
        if not result and query_value.lstrip("0") != query_value:
            query[field] = query_value.lstrip("0")
            result = collection.find_one(query)

        if result and "_id" in result:
            del result["_id"]  # Remove Mongo's default ID

        return result
    except Exception as e:
        print("❌ MongoDB Query Error:", e)
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1

    result = None
    message = None
    selected_option = "consumer"

    if request.method == "POST":
        selected_option = request.form.get("search_type", "consumer")
        input_value = request.form.get("input_value", "").strip()

        if input_value:
            result = get_consumer_data(input_value, selected_option)
            if not result:
                message = f"No data found for {selected_option} number: {input_value}"
        else:
            message = "Please enter a value."

    return render_template("index.html", result=result, message=message, selected=selected_option, visits=visit_counter)

@app.route("/download", methods=["POST"])
def download_csv():
    try:
        result_json = request.form.get("csv_data")
        if not result_json:
            return "No data", 400

        data = json.loads(result_json)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(data.keys())
        writer.writerow(data.values())
        output.seek(0)

        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='consumer_data.csv'
        )
    except Exception as e:
        print("❌ CSV Export Error:", e)
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)

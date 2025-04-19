import json
import io
import csv
from flask import Flask, render_template, request, send_file
from pymongo import MongoClient

app = Flask(__name__)
visit_counter = 0

# MongoDB Connection
client = MongoClient("mongodb+srv://bobbykumaar:bXXck9xw91fSedzt@consumercluster.nooechs.mongodb.net/?retryWrites=true&w=majority&appName=ConsumerCluster")
db = client["consumer_database"]
collection = db["consumers"]

# Clean label filter for display
@app.template_filter('pretty_key')
def pretty_key(key):
    return {
        "meter_number": "Meter Number"
    }.get(key, key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip())

# Get unique columns (with alias normalization)
def get_all_columns():
    columns = set()
    for doc in collection.find().limit(10):
        columns.update(doc.keys())
    columns.discard("_id")
    columns.discard("source")
    columns.discard("New Meter Qr Code")
    columns.discard("MSN")
    columns.add("meter_number")  # Add unified option
    return sorted(columns)

# Fetch matching data
def get_consumer_data(value, field):
    try:
        cross_fields = {
            "meter_number": ["New Meter Qr Code", "MSN"]
        }
        results = []

        # If cross-source search
        if field in cross_fields:
            for f in cross_fields[field]:
                q = {f: value}
                result = collection.find_one(q) or collection.find_one({f: value.lstrip("0")})
                if result:
                    result.pop("_id", None)
                    results.append(result)
        else:
            q = {field: value}
            result = collection.find_one(q) or collection.find_one({field: value.lstrip("0")})
            if result:
                result.pop("_id", None)
                results.append(result)

        return results
    except Exception as e:
        print("❌ MongoDB Query Error:", e)
        return []

# Home page
@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1

    result = []
    message = None
    selected_column = None
    search_value = ""
    all_columns = get_all_columns()

    if request.method == "POST":
        selected_column = request.form.get("search_column")
        search_value = request.form.get("input_value", "").strip()

        if selected_column and search_value:
            result = get_consumer_data(search_value, selected_column)
            if not result:
                message = f"No data found for {selected_column}: {search_value}"
        else:
            message = "Please select a column and enter a value."

    return render_template(
        "index.html",
        result=result,
        message=message,
        visits=visit_counter,
        all_columns=all_columns,
        selected_column=selected_column,
        input_value=search_value
    )

# CSV export
@app.route("/download", methods=["POST"])
def download_csv():
    try:
        result_json = request.form.get("csv_data")
        if not result_json:
            return "No data", 400

        data = json.loads(result_json)
        output = io.StringIO()
        writer = csv.writer(output)

        for record in data:
            if writer.tell() == 0:
                writer.writerow(record.keys())  # Write header
            writer.writerow(record.values())

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

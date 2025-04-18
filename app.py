import json
import io
import csv
from flask import Flask, render_template, request, send_file
from pymongo import MongoClient

app = Flask(__name__)
visit_counter = 0

# ✅ MongoDB Connection
client = MongoClient("mongodb+srv://bobbykumaar:bXXck9xw91fSedzt@consumercluster.nooechs.mongodb.net/?retryWrites=true&w=majority&appName=ConsumerCluster")
db = client["consumer_database"]
collection = db["consumers"]

# ✅ Template filter to clean column names
@app.template_filter('pretty_key')
def pretty_key(key):
    return key.replace('_', ' ').title().replace("Summary", "").replace("Styra", "").strip()

# ✅ Get all unique columns from a few sample documents
def get_all_columns():
    columns = set()
    for doc in collection.find().limit(10):
        columns.update(doc.keys())
    columns.discard("_id")
    columns.discard("source")
    return sorted(columns)

# ✅ Query the database by selected field and string value
def get_consumer_data(value, field):
    try:
        query = {field: value}
        print(f"🔍 Searching with query: {query}")
        result = collection.find_one(query)

        if not result and value.lstrip("0") != value:
            query[field] = value.lstrip("0")
            print(f"🔁 Retrying with stripped leading zeros: {query}")
            result = collection.find_one(query)

        if result:
            result.pop("_id", None)
        return result
    except Exception as e:
        print("❌ MongoDB Query Error:", e)
        return None

# ✅ Main route
@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1

    result = None
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

# ✅ CSV download endpoint
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

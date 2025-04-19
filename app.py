import json
import io
import csv
from flask import Flask, render_template, request, send_file
from pymongo import MongoClient

app = Flask(__name__)
visit_counter = 0

# Connect to MongoDB
client = MongoClient("mongodb+srv://bobbykumaar:bXXck9xw91fSedzt@consumercluster.nooechs.mongodb.net/?retryWrites=true&w=majority&appName=ConsumerCluster")
db = client["consumer_database"]
collection = db["consumers"]

# Format key names for display
@app.template_filter('pretty_key')
def pretty_key(key):
    return key.replace('_', ' ').title().strip()

# Search by meter number in both sources
def get_meter_data(meter_number):
    try:
        meter_number = meter_number.strip()
        results = []

        # Search in Source A
        a_doc = collection.find_one({
            "source": "A",
            "$or": [
                {"New Meter Qr Code": meter_number},
                {"New Meter Qr Code": meter_number.lstrip("0")}
            ]
        })
        if a_doc:
            a_doc.pop("_id", None)
            results.append(a_doc)

        # Search in Source B
        b_doc = collection.find_one({
            "source": "B",
            "$or": [
                {"MSN": meter_number},
                {"MSN": meter_number.lstrip("0")}
            ]
        })
        if b_doc:
            b_doc.pop("_id", None)
            results.append(b_doc)

        # Merge all found documents
        if results:
            combined = {}
            for r in results:
                combined.update(r)
            return combined

        return None
    except Exception as e:
        print("❌ Error fetching meter data:", e)
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1
    result = None
    message = None
    input_value = ""

    if request.method == "POST":
        input_value = request.form.get("input_value", "").strip()
        if input_value:
            result = get_meter_data(input_value)
            if not result:
                message = f"No data found for meter number: {input_value}"
        else:
            message = "Please enter a meter number."

    return render_template("index.html", result=result, message=message, visits=visit_counter, input_value=input_value)

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

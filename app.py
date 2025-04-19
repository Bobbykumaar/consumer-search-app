import json
import io
import csv
from flask import Flask, render_template, request, send_file
from pymongo import MongoClient

app = Flask(__name__)
visit_counter = 0

# MongoDB connection
client = MongoClient("mongodb+srv://bobbykumaar:bXXck9xw91fSedzt@consumercluster.nooechs.mongodb.net/?retryWrites=true&w=majority&appName=ConsumerCluster")
db = client["consumer_database"]
collection = db["consumers"]

# Search in both sources for a meter number
def get_meter_data_all_sources(meter_number):
    meter_number = meter_number.strip()
    
    source_a_doc = collection.find_one({
        "source": "A",
        "$or": [
            {"New Meter QR Code": meter_number},
            {"New Meter QR Code": meter_number.lstrip("0")}
        ]
    })

    source_b_doc = collection.find_one({
        "source": "B",
        "$or": [
            {"MSN": meter_number},
            {"MSN": meter_number.lstrip("0")}
        ]
    })

    # Filter columns based on prefix: 'me', 'mm', 'ma', or 'c'
    def filter_columns(doc):
        if not doc:
            return {}
        return {key: value for key, value in doc.items() if key.lower().startswith(('me', 'mm', 'ma', 'c'))}

    # Filter the documents for both sources
    source_a_doc = filter_columns(source_a_doc)
    source_b_doc = filter_columns(source_b_doc)

    return {
        "source_a": source_a_doc,
        "source_b": source_b_doc
    }

@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1
    meter_number = ""
    result_a = None
    result_b = None
    message = None

    if request.method == "POST":
        meter_number = request.form.get("input_value", "").strip()
        if meter_number:
            data = get_meter_data_all_sources(meter_number)
            result_a = data["source_a"]
            result_b = data["source_b"]

            if not result_a and not result_b:
                message = f"No data found for meter number: {meter_number}"
        else:
            message = "Please enter a meter number."

    return render_template(
        "index.html",
        visits=visit_counter,
        input_value=meter_number,
        result_a=result_a,
        result_b=result_b,
        message=message
    )

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

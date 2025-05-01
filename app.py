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

def get_meter_data_all_sources(meter_number):
    meter_number = meter_number.strip()

    # Source A (HES/MI)
    source_a_doc = collection.find_one({
        "source": "A",
        "$or": [
            {"New Meter QR Code": meter_number},
            {"New Meter QR Code": meter_number.lstrip("0")}
        ]
    })

    # Source B (MDM)
    source_b_raw = collection.find_one({
        "source": "B",
        "$or": [
            {"MSN": meter_number},
            {"MSN": meter_number.lstrip("0")}
        ]
    })

    source_a_doc = source_a_doc if source_a_doc else {}

    # Format result_b into a message
    if source_b_raw:
        status = source_b_raw.get("MASTERDATASYNC_STATUS", "").upper()
        if status == "COMPLETED":
            mdm_summary = (
                f"Master Data Sync for this consumer is completed on "
                f"{source_b_raw.get('MASTERDATASYNC_DTTM')}. "
                f"This consumer belongs to cycle code {source_b_raw.get('CYCLECODE')}."
            )
        elif source_b_raw.get("MMR_STATUS", "").upper() == "SUCCESS":
            mdm_summary = (
                f"Mass meter replacement is complete on {source_b_raw.get('MMR_DTTM')}, MDS still pending. "
                f"This consumer belongs to cycle code {source_b_raw.get('CYCLECODE')} "
                f"having permanent consumer number {source_b_raw.get('CONSUMER_ID')}."
            )
        else:
            mdm_summary = "MCO completed."
    else:
        mdm_summary = "MCO completed."

    return {
        "source_a": source_a_doc,
        "mdm_summary": mdm_summary
    }

@app.route("/", methods=["GET", "POST"])
def index():
    global visit_counter
    visit_counter += 1
    meter_number = ""
    result_a = None
    mdm_summary = None
    message = None

    if request.method == "POST":
        meter_number = request.form.get("input_value", "").strip()
        if meter_number:
            data = get_meter_data_all_sources(meter_number)
            result_a = data["source_a"]
            mdm_summary = data["mdm_summary"]
            if not result_a:
                message = f"No data found for meter number: {meter_number}"
        else:
            message = "Please enter a meter number."

    return render_template(
        "index.html",
        visits=visit_counter,
        input_value=meter_number,
        result_a=result_a,
        mdm_summary=mdm_summary,
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

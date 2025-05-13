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
    master_status = str(source_b_raw.get("MASTERDATASYNC_STATUS", "")).strip().lower()
    mmr_status = str(source_b_raw.get("MMR_STATUS", "")).strip().lower()
    cycle_code = str(source_b_raw.get("CYCLECODE", "")).strip()
    note = ""
    if cycle_code != "8":
        note = " <strong>Note:</strong> If cycle code is not 8, DISCOM are requested to process the cycle code to 8 for billing."

    if master_status == "completed":
        mdm_summary = (
            f"✅ <strong>Master Data Sync</strong> for this consumer is <strong>completed</strong> on "
            f"<strong>{source_b_raw.get('MASTERDATASYNC_DTTM', 'N/A')}</strong>. "
            f"This consumer belongs to <strong>Cycle Code {cycle_code or 'N/A'}</strong> "
            f"with permanent <strong>Consumer Number {source_b_raw.get('CONSUMER_ID', 'N/A')}</strong>."
            f"{note}"
        )
    elif mmr_status == "success":
        mdm_summary = (
            f"✅ <strong>Mass Meter Replacement</strong> was <strong>completed</strong> on "
            f"<strong>{source_b_raw.get('MMR_DTTM', 'N/A')}</strong>, but MDS is still pending. "
            f"This consumer belongs to <strong>Cycle Code {cycle_code or 'N/A'}</strong> "
            f"with permanent <strong>Consumer Number {source_b_raw.get('CONSUMER_ID', 'N/A')}</strong>."
            f"{note}"
        )
    else:
        mdm_summary = "⚠️ <strong>MCO completed, but MMR and MDS are yet to be confirmed</strong>."
else:
    mdm_summary = "⚠️ <strong>MCO not pushed</strong>."


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

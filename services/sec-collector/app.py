# services/sec-collector/app.py
import boto3, json, os, time, uuid, logging
from prometheus_client import Counter, Gauge, start_http_server

queue_url = os.environ["SQS_URL"]
events_total = Counter("iam_events_total", "Total IAM events", ["risk"])
lag_gauge = Gauge("sqs_lag", "SQS approx messages")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("collector")
sqs = boto3.client("sqs")

def normalize(msg):
    d = json.loads(msg["Body"])
    action = d["detail"]["eventName"]
    entity = d["detail"]["userIdentity"].get("userName", "unknown")
    return {
        "id": str(uuid.uuid4()),
        "entity_id": entity,
        "source": "cloudtrail",
        "action": action,
        "ts": d["detail"]["eventTime"],
        "attributes": {"geo": d["detail"].get("sourceIPAddress","unknown")}
    }

if __name__ == "__main__":
    start_http_server(8000)
    while True:
        lag = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"])
        lag_gauge.set(float(lag["Attributes"]["ApproximateNumberOfMessages"]))
        resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=10)
        for m in resp.get("Messages", []):
            ev = normalize(m)
            risk = "high" if ev["action"] in {"CreateAccessKey","AttachUserPolicy"} else "low"
            events_total.labels(risk=risk).inc()
            log.info(json.dumps({"service":"collector","event":ev,"risk":risk}))
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=m["ReceiptHandle"])
        time.sleep(1)

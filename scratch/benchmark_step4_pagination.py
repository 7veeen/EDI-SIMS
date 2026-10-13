import os
import sys
import time
import json
import statistics

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from flask_jwt_extended import create_access_token


def benchmark_endpoint(client, url, headers, iterations=5):
    latencies = []
    response_size = 0
    record_count = 0

    for _ in range(iterations):
        t0 = time.perf_counter()
        resp = client.get(url, headers=headers)
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        response_size = len(resp.data)

        if resp.status_code == 200:
            data = resp.get_json()
            if isinstance(data, list):
                record_count = len(data)
            elif isinstance(data, dict):
                for key in ["purchase_orders", "shipments", "inventory", "stock_requests", "products", "notifications", "logs"]:
                    if key in data and isinstance(data[key], list):
                        record_count = len(data[key])
                        break

    return {
        "url": url,
        "iterations": iterations,
        "size_bytes": response_size,
        "record_count": record_count,
        "min_ms": round(min(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "max_ms": round(max(latencies), 2)
    }


def main():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        owner_token = create_access_token(identity="1", additional_claims={"role": "Owner"})
    headers = {"Authorization": f"Bearer {owner_token}"}

    comparisons = [
        ("Purchase Orders (Unpaginated / All)", "/api/purchase-orders/",
         "Purchase Orders (Paginated Page 1, size 20)", "/api/purchase-orders/?page=1&page_size=20"),
        ("Shipments (Unpaginated / All)", "/api/shipments/",
         "Shipments (Paginated Page 1, size 20)", "/api/shipments/?page=1&page_size=20"),
        ("Inventory (Unpaginated / All)", "/api/inventory/",
         "Inventory (Paginated Page 1, size 20)", "/api/inventory/?page=1&page_size=20"),
        ("Stock Requests (Unpaginated / All)", "/api/stock-requests/",
         "Stock Requests (Paginated Page 1, size 20)", "/api/stock-requests/?page=1&page_size=20"),
        ("Notifications (Unpaginated / All)", "/api/notifications/",
         "Notifications (Paginated Page 1, size 20)", "/api/notifications/?page=1&page_size=20"),
    ]

    print("==========================================================================================")
    print("SIMS IMPROVEMENT 8 — PHASE 2 STEP 4: EMPIRICAL PAGINATION BENCHMARK")
    print("==========================================================================================")

    results = []
    for unpag_label, unpag_url, pag_label, pag_url in comparisons:
        print(f"\nBenchmarking: {unpag_label}...")
        res_unpag = benchmark_endpoint(client, unpag_url, headers)
        print(f"  -> Size: {res_unpag['size_bytes']:,} B | Median: {res_unpag['median_ms']} ms | Records: {res_unpag['record_count']}")

        print(f"Benchmarking: {pag_label}...")
        res_pag = benchmark_endpoint(client, pag_url, headers)
        print(f"  -> Size: {res_pag['size_bytes']:,} B | Median: {res_pag['median_ms']} ms | Records: {res_pag['record_count']}")

        reduction_bytes = res_unpag['size_bytes'] - res_pag['size_bytes']
        reduction_pct = round((reduction_bytes / res_unpag['size_bytes']) * 100.0, 1) if res_unpag['size_bytes'] > 0 else 0

        results.append({
            "entity": unpag_label.split(" (")[0],
            "unpag_size": res_unpag['size_bytes'],
            "pag_size": res_pag['size_bytes'],
            "size_reduction_pct": reduction_pct,
            "unpag_records": res_unpag['record_count'],
            "pag_records": res_pag['record_count'],
            "unpag_median_ms": res_unpag['median_ms'],
            "pag_median_ms": res_pag['median_ms']
        })

    print("\n\n" + "=" * 90)
    print(f"{'Endpoint Entity':<20} | {'Unpag Size':<12} | {'Pag Size':<12} | {'Payload Reduction':<18} | {'Latency (Unpag -> Pag)':<22}")
    print("=" * 90)
    for r in results:
        print(f"{r['entity']:<20} | {r['unpag_size']:>8,} B   | {r['pag_size']:>8,} B   | {r['size_reduction_pct']:>6.1f}% reduction   | {r['unpag_median_ms']}ms -> {r['pag_median_ms']}ms")
    print("=" * 90)

    # Save to json file for report inclusion
    out_path = os.path.join(os.path.dirname(__file__), "step4_benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()

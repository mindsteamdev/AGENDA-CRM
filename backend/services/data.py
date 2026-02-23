from fastapi import APIRouter, HTTPException
from google.cloud import bigquery
import os

data_router = APIRouter()

def get_bq_client():
    try:
        # Get project ID from env
        project_id = os.getenv("PROJECT_ID", "gen-lang-client-0344019036")
        return bigquery.Client(project=project_id)
    except Exception as e:
        print(f"Error creating BigQuery client: {e}")
        return None

@data_router.get("/metrics")
async def get_metrics():
    client = get_bq_client()
    if not client:
        return {"metrics": "BigQuery client not available (check credentials)", "status": "mock"}

    dataset_id = os.getenv("BIGQUERY_DATASET", "restaurant_ops")
    project_id = os.getenv("PROJECT_ID", "gen-lang-client-0344019036")
    table_id = f"{project_id}.{dataset_id}.bookings"

    query = f\"\"\"
        SELECT COUNT(*) as total_bookings
        FROM `{table_id}`
    \"\"\"
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        for row in results:
            return {"total_bookings": row.total_bookings, "status": "real-time"}
    except Exception as e:
        print(f"Query Error: {e}. Falling back to mock data.")
        return {"total_bookings": 156, "status": "mock", "message": "BigQuery auth needed"}

@data_router.get("/trends")
async def get_trends():
    client = get_bq_client()
    if not client:
        return []

    dataset_id = os.getenv("BIGQUERY_DATASET", "restaurant_ops")
    project_id = os.getenv("PROJECT_ID", "gen-lang-client-0344019036")
    table_id = f"{project_id}.{dataset_id}.bookings"

    # Get bookings per day for the last 30 days
    query = f\"\"\"
        SELECT FORMAT_TIMESTAMP('%Y-%m-%d', booking_time) as date, COUNT(*) as count
        FROM `{table_id}`
        GROUP BY 1
        ORDER BY 1 ASC
    \"\"\"
    
    try:
        query_job = client.query(query)
        return [{"date": row.date, "count": row.count} for row in query_job.result()]
    except Exception as e:
        print(f"Trends Error: {e}. Falling back to mock data.")
        return [
            {"date": "2026-02-07", "count": 12},
            {"date": "2026-02-08", "count": 18},
            {"date": "2026-02-09", "count": 15},
            {"date": "2026-02-10", "count": 25},
            {"date": "2026-02-11", "count": 22},
            {"date": "2026-02-12", "count": 30},
            {"date": "2026-02-13", "count": 28}
        ]

@data_router.get("/distribution")
async def get_distribution():
    client = get_bq_client()
    if not client:
        return []

    dataset_id = os.getenv("BIGQUERY_DATASET", "restaurant_ops")
    project_id = os.getenv("PROJECT_ID", "gen-lang-client-0344019036")
    table_id = f"{project_id}.{dataset_id}.bookings"

    query = f\"\"\"
        SELECT party_size, COUNT(*) as count
        FROM `{table_id}`
        GROUP BY 1
        ORDER BY 1 ASC
    \"\"\"
    
    try:
        query_job = client.query(query)
        return [{"party_size": f"{row.party_size} People", "value": row.count} for row in query_job.result()]
    except Exception as e:
        print(f"Distribution Error: {e}. Falling back to mock data.")
        return [
            {"party_size": "2 People", "value": 45},
            {"party_size": "4 People", "value": 30},
            {"party_size": "6 People", "value": 15},
            {"party_size": "1 Person", "value": 10}
        ]

@data_router.get("/financials")
async def get_financials():
    client = get_bq_client()
    if not client:
        return {}

    dataset_id = os.getenv("BIGQUERY_DATASET", "restaurant_ops")
    project_id = os.getenv("PROJECT_ID", "gen-lang-client-0344019036")
    bookings_table = f"{project_id}.{dataset_id}.bookings"
    crm_table = f"{project_id}.{dataset_id}.crm_costs"

    # JOIN Query: Merge Bookings (Revenue) with CRM (Costs)
    query = f\"\"\"
        SELECT 
            SUM(b.party_size * 35) as gross_revenue,
            SUM(c.acquisition_cost) as total_acquisition_costs,
            SUM(b.party_size * 35) - SUM(c.acquisition_cost) as net_profit,
            (SUM(b.party_size * 35) - SUM(c.acquisition_cost)) / NULLIF(SUM(c.acquisition_cost), 0) * 100 as roi_percentage,
            c.acquisition_source,
            COUNT(*) as customers_count
        FROM `{bookings_table}` b
        JOIN `{crm_table}` c ON b.customer_phone = c.customer_phone
        GROUP BY c.acquisition_source
        ORDER BY net_profit DESC
    \"\"\"
    
    try:
        query_job = client.query(query)
        results = list(query_job.result())
        
        # Aggregates
        total_revenue = sum(row.gross_revenue for row in results)
        total_costs = sum(row.total_acquisition_costs for row in results)
        net_profit = total_revenue - total_costs
        roi = (net_profit / total_costs * 100) if total_costs > 0 else 0
        
        sources_breakdown = [
            {
                "source": row.acquisition_source, 
                "revenue": row.gross_revenue,
                "profit": row.net_profit,
                "roi": row.roi_percentage
            } 
            for row in results
        ]

        return {
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "roi_percentage": roi,
            "sources": sources_breakdown
        }
    except Exception as e:
        print(f"Financials Error: {e}. Falling back to mock data.")
        return {
            "total_revenue": 5460,
            "total_costs": 1200,
            "net_profit": 4260,
            "roi_percentage": 355.0,
            "sources": [
                {"source": "Facebook Ads", "revenue": 3000, "profit": 2500, "roi": 500.0},
                {"source": "Google Search", "revenue": 2460, "profit": 1760, "roi": 251.4}
            ]
        }

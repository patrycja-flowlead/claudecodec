import base64
import httpx
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI(title="Lemlist API Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

LEMLIST_BASE = "https://api.lemlist.com"


def make_auth_header(api_key: str) -> str:
    encoded = base64.b64encode(f"lemlist:{api_key}".encode()).decode()
    return f"Basic {encoded}"


@app.get("/api/campaigns")
async def list_campaigns(x_api_key: str = Header(...)):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{LEMLIST_BASE}/api/campaigns",
            headers={"Authorization": make_auth_header(x_api_key)},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str, x_api_key: str = Header(...)):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{LEMLIST_BASE}/api/campaigns/{campaign_id}",
            headers={"Authorization": make_auth_header(x_api_key)},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@app.get("/api/activities")
async def list_activities(
    x_api_key: str = Header(...),
    type: Optional[str] = None,
    campaignId: Optional[str] = None,
    limit: int = 100,
):
    params = {"limit": limit}
    if type:
        params["type"] = type
    if campaignId:
        params["campaignId"] = campaignId

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{LEMLIST_BASE}/api/activities",
            headers={"Authorization": make_auth_header(x_api_key)},
            params=params,
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@app.get("/api/campaigns/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: str, x_api_key: str = Header(...)):
    """Aggregate key stats for a campaign in one call."""
    stat_types = [
        "emailsSent", "emailsOpened", "emailsClicked",
        "emailsReplied", "emailsBounced", "leadsAdded",
    ]
    results = {}
    async with httpx.AsyncClient() as client:
        auth = make_auth_header(x_api_key)
        for stat_type in stat_types:
            r = await client.get(
                f"{LEMLIST_BASE}/api/activities",
                headers={"Authorization": auth},
                params={"type": stat_type, "campaignId": campaign_id, "limit": 500},
            )
            if r.status_code == 200:
                data = r.json()
                results[stat_type] = len(data) if isinstance(data, list) else data.get("total", 0)
            else:
                results[stat_type] = 0

    sent = results.get("emailsSent", 0)
    opened = results.get("emailsOpened", 0)
    replied = results.get("emailsReplied", 0)
    clicked = results.get("emailsClicked", 0)

    results["openRate"] = round(opened / sent * 100, 1) if sent else 0
    results["replyRate"] = round(replied / sent * 100, 1) if sent else 0
    results["clickRate"] = round(clicked / opened * 100, 1) if opened else 0

    return results

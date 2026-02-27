import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def audit_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["diet_plan"]
    collections = await db.list_collection_names()
    
    report = "## MongoDB Audit\n\n"
    report += f"**Collections Found:** {collections}\n\n"
    
    for coll in collections:
        doc = await db[coll].find_one()
        report += f"### Collection: `{coll}`\n"
        if doc:
            report += "**Sample Document Keys:**\n"
            for k, v in doc.items():
                report += f"- `{k}` (Type: {type(v).__name__})\n"
        else:
            report += "*Collection is empty*\n"
        report += "\n"
        
    with open("db_audit_temp.md", "w") as f:
        f.write(report)
        
    client.close()

if __name__ == "__main__":
    asyncio.run(audit_db())

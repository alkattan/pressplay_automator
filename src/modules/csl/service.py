from sqlalchemy import select
from src.modules.csl.models import CSLModel, LocaleModel
from src.modules.app.models import AppModel
from typing import List, Dict

# def add_csls(session, data: List[Dict]) -> None:
#     """
#     Replace existing CSLs and their locales in the database for the given app
    
#     Args:
#         session: SQLAlchemy session
#         data (List[Dict]): List of dictionaries containing CSL data with format:
#             {
#                 "app": AppModel,
#                 "csl_play_console_id": str,
#                 "name": str,
#                 "locale": str
#             }
#     """
#     # Group data by CSL to avoid duplicates
#     csls_by_id = {}
#     for record in data:
#         if record["csl_play_console_id"] not in csls_by_id:
#             csls_by_id[record["csl_play_console_id"]] = {
#                 "app": record["app"],
#                 "name": record["name"],
#                 "locales": set()
#             }
#         csls_by_id[record["csl_play_console_id"]]["locales"].add(record["locale"])

#     # Get all existing CSLs for this app
#     app = data[0]["app"] if data else None
#     if not app:
#         return

#     # Delete existing CSLs for this app
#     existing_csls = session.scalars(
#         select(CSLModel).where(CSLModel.app_id == app.id)
#     ).all()
#     for csl in existing_csls:
#         session.delete(csl)
    
#     # Add new CSLs
#     for csl_id, csl_data in csls_by_id.items():
#         # Create new CSL
#         csl = CSLModel(
#             app_id=app.id,
#             name=csl_data["name"],
#             play_console_id=csl_id
#         )
#         session.add(csl)

#         # Handle locales
#         for locale_name in csl_data["locales"]:
#             # Get or create locale
#             locale = session.scalar(
#                 select(LocaleModel).where(LocaleModel.name == locale_name)
#             )
#             if not locale:
#                 locale = LocaleModel(name=locale_name)
#                 session.add(locale)
            
#             # Add locale to CSL
#             csl.locales.append(locale)

#     session.commit()

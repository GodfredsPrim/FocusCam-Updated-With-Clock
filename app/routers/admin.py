from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Vote, get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/results")
def get_results(db: Session = Depends(get_db)) -> dict:
	rows = db.execute(select(Vote.candidate, func.count(Vote.id)).group_by(Vote.candidate)).all()
	counts = {candidate: count for candidate, count in rows}
	return {
		"A": counts.get("A", 0),
		"B": counts.get("B", 0),
		"total": counts.get("A", 0) + counts.get("B", 0),
		"by_candidate": counts,
	}


@router.get("", response_class=HTMLResponse)
def admin_index(db: Session = Depends(get_db)):
	rows = db.execute(select(Vote.candidate, func.count(Vote.id)).group_by(Vote.candidate)).all()
	counts = {candidate: count for candidate, count in rows}
	A = counts.get("A", 0)
	B = counts.get("B", 0)
	total = A + B
	html = f"""
	<!DOCTYPE html>
	<html>
	<head>
		<meta charset=\"utf-8\" />
		<title>USSD Voting Results</title>
		<style>
			body {{ font-family: Arial, sans-serif; margin: 2rem; }}
			table {{ border-collapse: collapse; }}
			td, th {{ border: 1px solid #ddd; padding: 8px; }}
			th {{ background: #f4f4f4; }}
		</style>
	</head>
	<body>
		<h1>USSD Voting Results</h1>
		<table>
			<thead>
				<tr><th>Candidate</th><th>Votes</th></tr>
			</thead>
			<tbody>
				<tr><td>Candidate A</td><td>{A}</td></tr>
				<tr><td>Candidate B</td><td>{B}</td></tr>
				<tr><th>Total</th><th>{total}</th></tr>
			</tbody>
		</table>
	</body>
	</html>
	"""
	return html
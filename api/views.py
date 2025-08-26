# d:\sonlh6\Fantasy\api\views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from .models import Manager

FPL_API_URL_BOOTSTRAP = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_API_URL_ENTRY = "https://fantasy.premierleague.com/api/entry/{}/"
FPL_API_URL_HISTORY = "https://fantasy.premierleague.com/api/entry/{}/history/"

def test_connection(request):
    try:
        response = requests.get(FPL_API_URL_BOOTSTRAP)
        response.raise_for_status()
        data = response.json()
        current_gameweek = next((gw for gw in data['events'] if gw['is_current']), None)
        return JsonResponse({
            "success": True,
            "current_gameweek": current_gameweek['id'] if current_gameweek else 'N/A'
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({"success": False, "error": str(e)}, status=502)

@csrf_exempt
def add_manager(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            manager_id = int(body.get('manager_id'))
            if not manager_id:
                return JsonResponse({"success": False, "error": "Manager ID is required."}, status=400)

            if Manager.objects.filter(id=manager_id).exists():
                return JsonResponse({"success": False, "error": f"Manager ID {manager_id} đã có trong danh sách."}, status=400)

            response = requests.get(FPL_API_URL_ENTRY.format(manager_id))
            response.raise_for_status()
            data = response.json()

            new_manager = Manager.objects.create(
                id=data['id'],
                name=f"{data['player_first_name']} {data['player_last_name']}",
                team_name=data['name']
            )

            manager_data = {
                "id": new_manager.id,
                "name": new_manager.name,
                "team_name": new_manager.team_name,
            }
            return JsonResponse({"success": True, "manager": manager_data})
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return JsonResponse({"success": False, "error": f"Manager ID {manager_id} không tồn tại."}, status=404)
            return JsonResponse({"success": False, "error": f"Lỗi FPL API: {e}"}, status=502)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

def get_manager_stats(request, manager_id):
    try:
        entry_res = requests.get(FPL_API_URL_ENTRY.format(manager_id)); entry_res.raise_for_status(); entry_data = entry_res.json()
        history_res = requests.get(FPL_API_URL_HISTORY.format(manager_id)); history_res.raise_for_status(); history_data = history_res.json()
        gameweek_points, total_points, highest_gw, lowest_gw = [], 0, None, None
        for gw in history_data.get('current', []):
            total_points = gw['total_points']
            gameweek_points.append({"gameweek": gw['event'], "points": gw['points'], "total_points": gw['total_points'], "rank": gw['rank'], "bank": gw['bank'] / 10.0, "value": gw['value'] / 10.0, "event_transfers": gw['event_transfers'], "event_transfers_cost": gw['event_transfers_cost'], "points_on_bench": gw['points_on_bench']})
            if not highest_gw or gw['points'] > highest_gw['points']: highest_gw = gw
            if not lowest_gw or gw['points'] < lowest_gw['points']: lowest_gw = gw
        gameweeks_played = len(gameweek_points)
        average_points = round(total_points / gameweeks_played) if gameweeks_played > 0 else 0
        stats = {"manager_info": {"player_first_name": entry_data['player_first_name'], "player_last_name": entry_data['player_last_name'], "name": entry_data['name']}, "total_points": total_points, "average_points": average_points, "highest_gameweek": highest_gw, "lowest_gameweek": lowest_gw, "gameweeks_played": gameweeks_played, "gameweek_points": gameweek_points}
        return JsonResponse({"success": True, "data": stats})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@csrf_exempt
def compare_managers(request):
    if request.method == 'POST':
        try:
            manager_ids = json.loads(request.body).get('manager_ids', [])
            all_managers_data = []
            for manager_id in manager_ids:
                entry_res = requests.get(FPL_API_URL_ENTRY.format(manager_id)); entry_res.raise_for_status(); entry_data = entry_res.json()
                history_res = requests.get(FPL_API_URL_HISTORY.format(manager_id)); history_res.raise_for_status(); history_data = history_res.json()
                all_managers_data.append({"id": entry_data['id'], "name": f"{entry_data['player_first_name']} {entry_data['player_last_name']}", "team_name": entry_data['name'], "total_points": entry_data['summary_overall_points'], "gameweeks": [{"gameweek": gw['event'], "points": gw['points']} for gw in history_data.get('current', [])]})
            return JsonResponse({"success": True, "data": {"managers": all_managers_data}})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

@csrf_exempt
def remove_manager(request, manager_id):
    if request.method == 'DELETE':
        try:
            manager_to_delete = Manager.objects.get(id=manager_id)
            manager_to_delete.delete()
            return JsonResponse({"success": True, "message": f"Manager {manager_id} đã được xóa."})
        except Manager.DoesNotExist:
            return JsonResponse({"success": False, "error": "Manager không tồn tại."}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

@csrf_exempt
def clear_all_managers(request):
    if request.method == 'POST':
        try:
            count, _ = Manager.objects.all().delete()
            return JsonResponse({"success": True, "message": f"Đã xóa {count} manager."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)

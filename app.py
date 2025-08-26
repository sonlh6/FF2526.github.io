from flask import Flask, render_template, jsonify, request, session
import requests
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FantasyAPI:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_manager_info(self, manager_id: int) -> Optional[Dict]:
        """Lấy thông tin manager"""
        try:
            url = f"{self.base_url}entry/{manager_id}/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting manager info: {e}")
            return None
    
    def get_manager_history(self, manager_id: int) -> Optional[Dict]:
        """Lấy lịch sử điểm của manager qua các gameweek"""
        try:
            url = f"{self.base_url}entry/{manager_id}/history/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting manager history: {e}")
            return None
    
    def get_gameweek_picks(self, manager_id: int, gameweek: int) -> Optional[Dict]:
        """Lấy đội hình của manager trong gameweek cụ thể"""
        try:
            url = f"{self.base_url}entry/{manager_id}/event/{gameweek}/picks/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting gameweek picks: {e}")
            return None
    
    def get_league_standings(self, league_id: int) -> Optional[Dict]:
        """Lấy bảng xếp hạng của league"""
        try:
            url = f"{self.base_url}leagues-classic/{league_id}/standings/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting league standings: {e}")
            return None
    
    def get_bootstrap_static(self) -> Optional[Dict]:
        """Lấy dữ liệu cơ bản của game (players, teams, gameweeks)"""
        try:
            url = f"{self.base_url}bootstrap-static/"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting bootstrap data: {e}")
            return None

class FantasyStatsTracker:
    def __init__(self):
        self.api = FantasyAPI()
        self.managers_data = {}
        
    def add_manager(self, manager_id: int) -> bool:
        """Thêm manager vào danh sách theo dõi"""
        try:
            manager_info = self.api.get_manager_info(manager_id)
            if manager_info:
                self.managers_data[manager_id] = {
                    'info': manager_info,
                    'history': None,
                    'last_updated': None
                }
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding manager {manager_id}: {e}")
            return False
    
    def update_manager_data(self, manager_id: int) -> bool:
        """Cập nhật dữ liệu của manager"""
        try:
            if manager_id not in self.managers_data:
                return False
            
            history = self.api.get_manager_history(manager_id)
            if history:
                self.managers_data[manager_id]['history'] = history
                self.managers_data[manager_id]['last_updated'] = datetime.now()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating manager {manager_id}: {e}")
            return False
    
    def get_manager_stats(self, manager_id: int) -> Optional[Dict]:
        """Lấy thống kê chi tiết của manager"""
        if manager_id not in self.managers_data:
            return None
        
        data = self.managers_data[manager_id]
        if not data['history']:
            return None
        
        history = data['history']
        current_season = history.get('current', [])
        
        if not current_season:
            return None
        
        # Tính toán các thống kê
        total_points = sum(gw['points'] for gw in current_season)
        gameweeks_played = len(current_season)
        avg_points = total_points / gameweeks_played if gameweeks_played > 0 else 0
        
        highest_gw = max(current_season, key=lambda x: x['points']) if current_season else None
        lowest_gw = min(current_season, key=lambda x: x['points']) if current_season else None
        
        # Điểm theo từng gameweek
        gameweek_points = [
            {
                'gameweek': gw['event'],
                'points': gw['points'],
                'total_points': gw['total_points'],
                'rank': gw['overall_rank'],
                'bank': gw['bank'] / 10,  # Convert to millions
                'value': gw['value'] / 10,
                'event_transfers': gw['event_transfers'],
                'event_transfers_cost': gw['event_transfers_cost'],
                'points_on_bench': gw['points_on_bench']
            }
            for gw in current_season
        ]
        
        return {
            'manager_info': data['info'],
            'total_points': total_points,
            'gameweeks_played': gameweeks_played,
            'average_points': round(avg_points, 1),
            'highest_gameweek': highest_gw,
            'lowest_gameweek': lowest_gw,
            'gameweek_points': gameweek_points,
            'last_updated': data['last_updated']
        }
    
    def compare_managers(self, manager_ids: List[int]) -> Dict:
        """So sánh nhiều managers"""
        comparison = {
            'managers': [],
            'gameweek_comparison': []
        }
        
        # Lấy data của các managers
        managers_stats = []
        for manager_id in manager_ids:
            stats = self.get_manager_stats(manager_id)
            if stats:
                managers_stats.append({
                    'id': manager_id,
                    'name': stats['manager_info']['player_first_name'] + ' ' + stats['manager_info']['player_last_name'],
                    'team_name': stats['manager_info']['name'],
                    'total_points': stats['total_points'],
                    'average_points': stats['average_points'],
                    'gameweeks': stats['gameweek_points']
                })
        
        comparison['managers'] = managers_stats
        
        # Tạo comparison theo gameweek
        if managers_stats:
            max_gameweeks = max(len(m['gameweeks']) for m in managers_stats)
            
            for gw in range(1, max_gameweeks + 1):
                gw_data = {'gameweek': gw, 'managers': []}
                
                for manager in managers_stats:
                    gw_points = next((g['points'] for g in manager['gameweeks'] if g['gameweek'] == gw), 0)
                    gw_total = next((g['total_points'] for g in manager['gameweeks'] if g['gameweek'] == gw), 0)
                    
                    gw_data['managers'].append({
                        'id': manager['id'],
                        'name': manager['name'],
                        'points': gw_points,
                        'total_points': gw_total
                    })
                
                comparison['gameweek_comparison'].append(gw_data)
        
        return comparison

# Khởi tạo tracker
tracker = FantasyStatsTracker()

@app.route('/')
def index():
    """Trang chính"""
    return render_template('fantasy_dashboard.html')

@app.route('/api/add-manager', methods=['POST'])
def add_manager():
    """API thêm manager"""
    try:
        data = request.json
        manager_id = int(data.get('manager_id', 0))
        
        if manager_id <= 0:
            return jsonify({'success': False, 'error': 'Manager ID không hợp lệ'})
        
        success = tracker.add_manager(manager_id)
        if success:
            # Update data ngay lập tức
            tracker.update_manager_data(manager_id)
            
            # Lưu vào session
            if 'managers' not in session:
                session['managers'] = []
            if manager_id not in session['managers']:
                session['managers'].append(manager_id)
            
            manager_info = tracker.managers_data[manager_id]['info']
            return jsonify({
                'success': True,
                'manager': {
                    'id': manager_id,
                    'name': f"{manager_info['player_first_name']} {manager_info['player_last_name']}",
                    'team_name': manager_info['name']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Không tìm thấy manager hoặc lỗi API'})
            
    except ValueError:
        return jsonify({'success': False, 'error': 'Manager ID phải là số'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/manager/<int:manager_id>/stats')
def get_manager_stats(manager_id):
    """API lấy thống kê manager"""
    try:
        # Update data trước khi lấy stats
        tracker.update_manager_data(manager_id)
        
        stats = tracker.get_manager_stats(manager_id)
        if stats:
            return jsonify({'success': True, 'data': stats})
        else:
            return jsonify({'success': False, 'error': 'Không có dữ liệu cho manager này'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/compare-managers', methods=['POST'])
def compare_managers():
    """API so sánh managers"""
    try:
        data = request.json
        manager_ids = [int(id) for id in data.get('manager_ids', [])]
        
        if not manager_ids:
            return jsonify({'success': False, 'error': 'Chưa chọn managers để so sánh'})
        
        # Update data cho tất cả managers
        for manager_id in manager_ids:
            tracker.update_manager_data(manager_id)
        
        comparison = tracker.compare_managers(manager_ids)
        return jsonify({'success': True, 'data': comparison})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove-manager/<int:manager_id>', methods=['DELETE'])
def remove_manager(manager_id):
    """API xóa manager"""
    try:
        if manager_id in tracker.managers_data:
            del tracker.managers_data[manager_id]
        
        # Xóa khỏi session
        if 'managers' in session and manager_id in session['managers']:
            session['managers'].remove(manager_id)
        
        return jsonify({'success': True, 'message': 'Đã xóa manager'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/managers')
def get_managers():
    """API lấy danh sách managers đã thêm"""
    try:
        managers = []
        session_managers = session.get('managers', [])
        
        for manager_id in session_managers:
            if manager_id in tracker.managers_data:
                manager_info = tracker.managers_data[manager_id]['info']
                managers.append({
                    'id': manager_id,
                    'name': f"{manager_info['player_first_name']} {manager_info['player_last_name']}",
                    'team_name': manager_info['name'],
                    'last_updated': tracker.managers_data[manager_id]['last_updated'].isoformat() if tracker.managers_data[manager_id]['last_updated'] else None
                })
        
        return jsonify({'success': True, 'data': managers})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/league/<int:league_id>')
def get_league_standings(league_id):
    """API lấy bảng xếp hạng league"""
    try:
        standings = tracker.api.get_league_standings(league_id)
        if standings:
            return jsonify({'success': True, 'data': standings})
        else:
            return jsonify({'success': False, 'error': 'Không tìm thấy league'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test-connection')
def test_connection():
    """Test kết nối API"""
    try:
        bootstrap_data = tracker.api.get_bootstrap_static()
        if bootstrap_data:
            current_gw = next((gw for gw in bootstrap_data['events'] if gw['is_current']), None)
            return jsonify({
                'success': True, 
                'message': 'Kết nối API thành công',
                'current_gameweek': current_gw['id'] if current_gw else 'N/A'
            })
        else:
            return jsonify({'success': False, 'error': 'Không thể kết nối API'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
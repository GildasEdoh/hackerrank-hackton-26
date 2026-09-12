import csv
import re
from datetime import datetime

def parse_messages():
    with open('dataset/messages.csv', 'r', encoding='utf-8') as f:
        messages = list(csv.DictReader(f))
        
    user_updates = {}
    
    for m in messages:
        uid = m['user_id']
        txt = m['message_text']
        src = m['source_type']
        
        if uid not in user_updates:
            user_updates[uid] = {
                'salary_amount': None,
                'salary_start_date': None,
                'salary_date': None,
                'salary_ended': False,
                'rent_multiplier': 1.0,
                'notes': []
            }
            
        up = user_updates[uid]
        
        # 1. Seasonal / Employment ended
        if any(w in txt.lower() for w in ['seasonal contract has ended', 'kontrak musiman saat ini telah berakhir', 'employment has ended', 'pendapatan kerja rumah tangga telah berakhir']):
            up['salary_ended'] = True
            up['notes'].append('salary_ended')
            
        # 2. Rent increase
        rent_match = re.search(r'rent by (\d+)%|sewa menaikkan biaya.*?(\d+)%', txt, re.IGNORECASE)
        if rent_match:
            pct = int(rent_match.group(1) or rent_match.group(2))
            up['rent_multiplier'] = 1.0 + pct / 100.0
            up['notes'].append(f'rent_increase_{pct}%')
            
        # 3. Date replacement (e.g. "confirmed salary is now expected on 2024-09-23")
        date_match = re.search(r'(?:expected on|jadwal.*?tanggal)\s*(\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if date_match:
            up['salary_date'] = date_match.group(1)
            up['notes'].append(f'salary_date_{date_match.group(1)}')
            
        # 4. Salary amounts:
        # e.g., "naik menjadi IDR 42750000", "temporary monthly pay is EUR 1037.52", "next salary is reduced to EUR 1422.85",
        # "first salary will be EUR 1661", "confirmed base salary is USD 1548", "Regular salary of EUR 2717 resumes on 2025-08-15"
        amt_match = re.search(r'(?:naik menjadi|gaji pertama.*?sebesar|is now expected to be|first salary (?:will be|is scheduled for|from the new employer is)|temporary monthly pay is|next salary is reduced to|gaji rutin.*?adalah|gaji pokok yang dikonfirmasi adalah|regular salary (?:for the next payroll|of [A-Z]{3} \d+) resumes on|confirmed base salary is|approved an invoice payment of|salary of [A-Z]{3} \d+ is confirmed for|regular salary for the next payroll is)\s*([A-Z]{3})?\s*([\d,]+(?:\.\d+)?)', txt, re.IGNORECASE)
        if amt_match:
            amt_str = amt_match.group(2).replace(',', '')
            up['salary_amount'] = float(amt_str)
            up['notes'].append(f'salary_amt_{amt_str}')
            
        # Resume date
        resume_match = re.search(r'resumes on\s*(\d{4}-\d{2}-\d{2})|berlaku mulai\s*(\d{4}-\d{2}-\d{2})|scheduled for\s*(\d{4}-\d{2}-\d{2})|confirmed for\s*(\d{4}-\d{2}-\d{2})', txt, re.IGNORECASE)
        if resume_match:
            d_str = resume_match.group(1) or resume_match.group(2) or resume_match.group(3) or resume_match.group(4)
            up['salary_start_date'] = d_str
            up['notes'].append(f'salary_start_{d_str}')

    return user_updates

if __name__ == '__main__':
    updates = parse_messages()
    print(f"Parsed updates for {len(updates)} users.")
    for uid in ['user_02', 'user_04', 'user_06', 'user_07', 'user_08', 'user_11', 'user_12', 'user_16']:
        print(uid, updates.get(uid))

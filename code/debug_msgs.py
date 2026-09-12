"""Check messages for key users."""
import csv, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

with open('dataset/messages.csv', 'r', encoding='utf-8') as f:
    msgs = list(csv.DictReader(f))

# All messages for user_05
print("user_05 messages:")
for m in msgs:
    if m['user_id'] == 'user_05':
        print(f"  id={m['message_id']} sent={m['sent_at']} src={m['source_type']}")
        print(f"  text: {m['message_text'][:400]}")
        print()

# All messages for users with misses
print("All messages by user:")
for uid in ['user_05', 'user_06', 'user_07', 'user_08', 'user_11', 'user_12', 'user_13', 'user_17', 'user_21']:
    user_msgs = [m for m in msgs if m['user_id'] == uid]
    if user_msgs:
        print(f"\n--- {uid} ({len(user_msgs)} messages) ---")
        for m in user_msgs:
            print(f"  [{m['sent_at']}] {m['source_type']}: {m['message_text'][:300]}")
    else:
        print(f"\n--- {uid}: NO MESSAGES ---")

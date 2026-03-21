"""Seed the REST database with ~30 realistic satsangi records."""

import json
import urllib.request

API = "http://localhost:8001/api/satsangis"

PEOPLE = [
    {"first_name": "Radha", "last_name": "Sharma", "phone_number": "9876543210", "age": 45, "gender": "Female", "city": "Vrindavan", "state": "Uttar Pradesh", "pincode": "281121", "nationality": "Indian", "country": "India", "introduced_by": "Preacher", "email": "radha.sharma@gmail.com"},
    {"first_name": "Krishna", "last_name": "Verma", "phone_number": "9988776655", "age": 38, "gender": "Male", "city": "Mathura", "state": "Uttar Pradesh", "pincode": "281001", "nationality": "Indian", "country": "India", "introduced_by": "TV", "has_room_in_ashram": True},
    {"first_name": "Meera", "last_name": "Bai", "phone_number": "8877665544", "age": 62, "gender": "Female", "city": "Jaipur", "state": "Rajasthan", "pincode": "302001", "nationality": "Indian", "country": "India", "special_category": "Senior Citizen", "first_timer": False},
    {"first_name": "Arjun", "last_name": "Patel", "phone_number": "7766554433", "age": 29, "gender": "Male", "city": "Ahmedabad", "state": "Gujarat", "pincode": "380001", "nationality": "Indian", "country": "India", "introduced_by": "Online", "first_timer": True},
    {"first_name": "Sita", "last_name": "Devi", "phone_number": "9123456789", "age": 55, "gender": "Female", "city": "Patna", "state": "Bihar", "pincode": "800001", "nationality": "Indian", "country": "India", "govt_id_type": "Aadhar Card", "govt_id_number": "1234-5678-9012"},
    {"first_name": "Govind", "last_name": "Das", "phone_number": "9234567890", "age": 41, "gender": "Male", "city": "Prayagraj", "state": "Uttar Pradesh", "pincode": "211001", "nationality": "Indian", "country": "India", "email": "govind.das@yahoo.com", "has_room_in_ashram": True},
    {"first_name": "Lakshmi", "last_name": "Iyer", "phone_number": "9345678901", "age": 33, "gender": "Female", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600001", "nationality": "Indian", "country": "India", "introduced_by": "Person"},
    {"first_name": "Ram", "last_name": "Kumar", "phone_number": "9456789012", "age": 50, "gender": "Male", "city": "Lucknow", "state": "Uttar Pradesh", "pincode": "226001", "nationality": "Indian", "country": "India", "nick_name": "Ramu", "print_on_card": True},
    {"first_name": "Ganga", "last_name": "Prasad", "phone_number": "9567890123", "age": 67, "gender": "Male", "city": "Varanasi", "state": "Uttar Pradesh", "pincode": "221001", "nationality": "Indian", "country": "India", "special_category": "Senior Citizen", "notes": "Long-time devotee, needs wheelchair access"},
    {"first_name": "Parvati", "last_name": "Singh", "phone_number": "9678901234", "age": 28, "gender": "Female", "city": "Delhi", "state": "Delhi", "pincode": "110001", "nationality": "Indian", "country": "India", "email": "parvati.singh@outlook.com", "first_timer": True},
    {"first_name": "Hari", "last_name": "Om", "phone_number": "9789012345", "age": 44, "gender": "Male", "city": "Bhopal", "state": "Madhya Pradesh", "pincode": "462001", "nationality": "Indian", "country": "India", "introduced_by": "Preacher", "has_room_in_ashram": True},
    {"first_name": "Tulsi", "last_name": "Agarwal", "phone_number": "9890123456", "age": 36, "gender": "Female", "city": "Agra", "state": "Uttar Pradesh", "pincode": "282001", "nationality": "Indian", "country": "India", "govt_id_type": "Passport", "govt_id_number": "J8765432"},
    {"first_name": "Bhakti", "last_name": "Mishra", "phone_number": "8765432109", "age": 52, "gender": "Female", "city": "Ranchi", "state": "Jharkhand", "pincode": "834001", "nationality": "Indian", "country": "India", "emergency_contact": "9876001234"},
    {"first_name": "Shyam", "last_name": "Sundar", "phone_number": "8654321098", "age": 31, "gender": "Male", "city": "Kolkata", "state": "West Bengal", "pincode": "700001", "nationality": "Indian", "country": "India", "introduced_by": "Online", "email": "shyam.sundar@gmail.com"},
    {"first_name": "Durga", "last_name": "Thapa", "phone_number": "9771234567", "age": 40, "gender": "Female", "city": "Kathmandu", "state": None, "pincode": None, "nationality": "Nepali", "country": "Nepal", "govt_id_type": "Nagrita (Nepal)", "govt_id_number": "NP-2024-78901"},
    {"first_name": "Binod", "last_name": "Chaudhary", "phone_number": "9779876543", "age": 35, "gender": "Male", "city": "Pokhara", "state": None, "pincode": None, "nationality": "Nepali", "country": "Nepal", "first_timer": True},
    {"first_name": "Saraswati", "last_name": "Joshi", "phone_number": "7543210987", "age": 48, "gender": "Female", "city": "Pune", "state": "Maharashtra", "pincode": "411001", "nationality": "Indian", "country": "India", "introduced_by": "TV", "notes": "Interested in weekly satsang"},
    {"first_name": "Mohan", "last_name": "Gupta", "phone_number": "7432109876", "age": 56, "gender": "Male", "city": "Kanpur", "state": "Uttar Pradesh", "pincode": "208001", "nationality": "Indian", "country": "India", "has_room_in_ashram": True, "govt_id_type": "Voter ID", "govt_id_number": "UP/08/123/456789"},
    {"first_name": "Anita", "last_name": "Rani", "phone_number": "7321098765", "age": 26, "gender": "Female", "city": "Chandigarh", "state": "Chandigarh", "pincode": "160001", "nationality": "Indian", "country": "India", "email": "anita.rani@gmail.com", "first_timer": True},
    {"first_name": "Damodar", "last_name": "Pandey", "phone_number": "7210987654", "age": 71, "gender": "Male", "city": "Haridwar", "state": "Uttarakhand", "pincode": "249401", "nationality": "Indian", "country": "India", "special_category": "Senior Citizen", "has_room_in_ashram": True, "notes": "Permanent resident at ashram"},
    {"first_name": "Kamala", "last_name": "Nair", "phone_number": "8109876543", "age": 39, "gender": "Female", "city": "Kochi", "state": "Kerala", "pincode": "682001", "nationality": "Indian", "country": "India", "introduced_by": "Person"},
    {"first_name": "Vijay", "last_name": "Tiwari", "phone_number": "8098765432", "age": 34, "gender": "Male", "city": "Indore", "state": "Madhya Pradesh", "pincode": "452001", "nationality": "Indian", "country": "India", "govt_id_type": "Driving License", "govt_id_number": "MP-0420211234567"},
    {"first_name": "Priya", "last_name": "Chopra", "phone_number": "7987654321", "age": 30, "gender": "Female", "city": "Mumbai", "state": "Maharashtra", "pincode": "400001", "nationality": "Indian", "country": "India", "email": "priya.chopra@hotmail.com", "introduced_by": "Online"},
    {"first_name": "Nand", "last_name": "Kishore", "phone_number": "7876543210", "age": 58, "gender": "Male", "city": "Bareilly", "state": "Uttar Pradesh", "pincode": "243001", "nationality": "Indian", "country": "India", "nick_name": "Nandu", "print_on_card": True},
    {"first_name": "Janaki", "last_name": "Raman", "phone_number": "7765432109", "age": 43, "gender": "Female", "city": "Hyderabad", "state": "Telangana", "pincode": "500001", "nationality": "Indian", "country": "India", "emergency_contact": "7712345678"},
    {"first_name": "Balram", "last_name": "Yadav", "phone_number": "7654321098", "age": 47, "gender": "Male", "city": "Gwalior", "state": "Madhya Pradesh", "pincode": "474001", "nationality": "Indian", "country": "India", "has_room_in_ashram": True, "introduced_by": "Preacher"},
    {"first_name": "Sunita", "last_name": "Kumari", "phone_number": "7543219876", "age": 25, "gender": "Female", "city": "Patna", "state": "Bihar", "pincode": "800002", "nationality": "Indian", "country": "India", "first_timer": True, "date_of_first_visit": "2026-03-10"},
    {"first_name": "Dinesh", "last_name": "Rawat", "phone_number": "6543210987", "age": 60, "gender": "Male", "city": "Dehradun", "state": "Uttarakhand", "pincode": "248001", "nationality": "Indian", "country": "India", "special_category": "Senior Citizen", "govt_id_type": "Aadhar Card", "govt_id_number": "9876-5432-1098"},
    {"first_name": "Manju", "last_name": "Dubey", "phone_number": "6432109876", "age": 37, "gender": "Female", "city": "Allahabad", "state": "Uttar Pradesh", "pincode": "211002", "nationality": "Indian", "country": "India", "address": "42, Civil Lines, Prayagraj", "email": "manju.dubey@gmail.com"},
    {"first_name": "Raghav", "last_name": "Shrestha", "phone_number": "9779871234", "age": 42, "gender": "Male", "city": "Biratnagar", "state": None, "pincode": None, "nationality": "Nepali", "country": "Nepal", "introduced_by": "Person", "first_timer": True},
]

def main():
    ok = 0
    fail = 0
    for p in PEOPLE:
        try:
            data = json.dumps(p).encode()
            req = urllib.request.Request(API, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = json.loads(resp.read())
            sid = body.get("satsangi_id", "?")
            print(f"  ✓ {p['first_name']} {p['last_name']} → {sid}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {p['first_name']} {p['last_name']} — {e}")
            fail += 1

    print(f"\nDone: {ok} created, {fail} failed (total: {len(PEOPLE)})")


if __name__ == "__main__":
    main()

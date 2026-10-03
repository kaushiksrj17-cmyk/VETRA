import sys
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

sys.path.insert(0, str(backend_dir))
sys.path.insert(1, str(root_dir))

from app.main import app


def run_tests():
    print("=" * 60)
    print("VETRA PHASE 6.6 — REGRESSION VERIFICATION")
    print("=" * 60)

    client = TestClient(app)

    # 1. Login Farmer
    r_farmer = client.post("/auth/login", json={"email": "farmer@vetra.demo", "password": "Vetra@12345"})
    assert r_farmer.status_code == 200, f"Farmer login failed: {r_farmer.text}"
    farmer_token = r_farmer.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    print("[PASS] 1. Farmer authenticated successfully.")

    # 2. Login Veterinarian
    r_vet = client.post("/auth/login", json={"email": "vet@vetra.demo", "password": "VetraVet@2026"})
    assert r_vet.status_code == 200, f"Vet login failed: {r_vet.text}"
    vet_token = r_vet.json()["access_token"]
    vet_id = r_vet.json()["user"]["id"]
    vet_name = r_vet.json()["user"]["full_name"]
    vet_headers = {"Authorization": f"Bearer {vet_token}"}
    print("[PASS] 2. Veterinarian authenticated successfully.")

    # 3. Get Farms and Animals
    r_farms = client.get("/farms", headers=farmer_headers)
    assert r_farms.status_code == 200 and len(r_farms.json()) > 0, "No farms found"
    farm_id = r_farms.json()[0]["id"]
    r_animals = client.get(f"/farms/{farm_id}/animals", headers=farmer_headers)
    assert r_animals.status_code == 200 and len(r_animals.json()) > 0, "No animals found"
    animal = r_animals.json()[0]
    animal_id = animal["id"]
    print(f"[PASS] 3. Loaded animal: {animal.get('name')} ({animal.get('tag_id')}) ID: {animal_id}")

    # 4. Check Veterinarians List
    r_vets_list = client.get("/veterinary-cases/veterinarians/list", headers=farmer_headers)
    assert r_vets_list.status_code == 200 and len(r_vets_list.json()) >= 1
    print(f"[PASS] 4. Veterinarians list endpoint returns {len(r_vets_list.json())} vets/admins.")

    # 5. Check Veterinary Cases for animal
    r_cases = client.get(f"/veterinary-cases/animal/{animal_id}", headers=farmer_headers)
    assert r_cases.status_code == 200
    print(f"[PASS] 5. Animal cases endpoint returns {len(r_cases.json())} existing cases.")

    print("=" * 60)
    print("PHASE 6.6 REGRESSION CHECK PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()

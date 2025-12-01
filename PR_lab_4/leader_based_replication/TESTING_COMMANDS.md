# Quick Test Commands for PR Lab 4

## Start the system

cd "d:\Universitate\Semestrul 5\PR\Labs\PR_labs\PR_lab_4\leader_based_replication"; docker-compose up --build

## In a NEW terminal, run these tests:

# Test 1: Write to leader

curl.exe -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{\"key\":\"test1\",\"value\":\"hello\"}'

# Test 2: Read from leader

curl.exe http://localhost:8000/get?key=test1

# Test 3: Read from follower (should have replicated)

curl.exe http://localhost:8001/get?key=test1

# Test 4: Dump all data from leader

curl.exe http://localhost:8000/dump

# Test 5: Dump from follower

curl.exe http://localhost:8001/dump

# Test 6: Multiple writes to same key (test race condition)

curl.exe -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{\"key\":\"race\",\"value\":\"v1\"}'
curl.exe -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{\"key\":\"race\",\"value\":\"v2\"}'
curl.exe -X POST http://localhost:8000/write -H "Content-Type: application/json" -d '{\"key\":\"race\",\"value\":\"v3\"}'

# Check if all replicas have same sequence number

curl.exe http://localhost:8000/get?key=race
curl.exe http://localhost:8001/get?key=race
curl.exe http://localhost:8002/get?key=race

## Stop the system

docker-compose down

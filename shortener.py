import boto3
import json
import os
import random
import string
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION'))
TABLE_NAME = os.getenv('TABLE_NAME')

def create_table():
    print(f"Creating DynamoDB table: {TABLE_NAME}...")
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'short_code', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'short_code', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        table.wait_until_exists()
        print(f"Table created\n")
        return table
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print(f"Table already exists\n")
            return dynamodb.Table(TABLE_NAME)
        raise e

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def shorten_url(table, long_url):
    short_code = generate_short_code()
    
    table.put_item(Item={
        'short_code': short_code,
        'long_url': long_url,
        'created_at': datetime.now().isoformat(),
        'clicks': 0
    })
    
    short_url = f"https://short.ly/{short_code}"
    print(f"Shortened: {long_url[:50]}... -> {short_url}")
    return short_code, short_url

def expand_url(table, short_code):
    response = table.get_item(Key={'short_code': short_code})
    item = response.get('Item')
    
    if item:
        # Update click count
        table.update_item(
            Key={'short_code': short_code},
            UpdateExpression='SET clicks = clicks + :val',
            ExpressionAttributeValues={':val': 1}
        )
        return item['long_url'], item['clicks'] + 1
    return None, 0

def get_stats(table, short_code):
    response = table.get_item(Key={'short_code': short_code})
    item = response.get('Item')
    if item:
        return {
            'short_code': short_code,
            'long_url': item['long_url'],
            'clicks': item['clicks'],
            'created_at': item['created_at']
        }
    return None

def teardown(table):
    print("\nTearing down table...")
    table.delete()
    print("Table deleted — no charges")

def run():
    print("Serverless URL Shortener")
    print("========================\n")

    # Step 1 — Setup
    print("Step 1: Setting up DynamoDB table...")
    table = create_table()

    # Step 2 — Shorten some URLs
    print("Step 2: Shortening URLs...")
    test_urls = [
        "https://github.com/AishatAnalytics/ai-morning-bot",
        "https://www.linkedin.com/in/aishatolatunji/",
        "https://console.aws.amazon.com/lambda/home",
        "https://github.com/AishatAnalytics/multi-region-failover",
        "https://docs.aws.amazon.com/solutions-architect"
    ]

    shortened = []
    for url in test_urls:
        short_code, short_url = shorten_url(table, url)
        shortened.append((short_code, url, short_url))

    # Step 3 — Simulate clicks
    print("\nStep 3: Simulating URL clicks...")
    for short_code, long_url, short_url in shortened[:3]:
        clicks = random.randint(1, 10)
        for _ in range(clicks):
            expand_url(table, short_code)
        print(f"Simulated {clicks} clicks on {short_url}")

    # Step 4 — Show stats
    print("\nStep 4: Showing URL stats...")
    print("\n" + "="*50)
    print("URL SHORTENER STATS")
    print("="*50)
    for short_code, long_url, short_url in shortened:
        stats = get_stats(table, short_code)
        if stats:
            print(f"\nShort URL: https://short.ly/{short_code}")
            print(f"Original: {long_url[:60]}...")
            print(f"Clicks: {stats['clicks']}")
            print(f"Created: {stats['created_at'][:19]}")

    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'urls_shortened': len(shortened),
        'urls': [
            {
                'short_code': sc,
                'long_url': lu,
                'short_url': su
            }
            for sc, lu, su in shortened
        ]
    }

    with open('shortener_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\nReport saved to shortener_report.json")

    # Teardown
    teardown(table)
    print("\nServerless URL Shortener complete!")

if __name__ == "__main__":
    run()
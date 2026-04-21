import sys, os, asyncio, datetime
sys.path.append(os.path.dirname(__file__))
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import init_db, get_all_listings
from notifications.telegram_bot import send_property_notification
from sheets_sync import save_listing_to_sheet, bulk_sync_db_to_sheet
from scrapers.njoftime import scrape_njoftime
from scrapers.merrjep import scrape_merrjep
from scrapers.instagram import scrape_instagram

FIRST_RUN_FLAG = os.path.join(os.path.dirname(__file__), '.first_run_done')

def run_scraper_job():
    now = datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    print(f'\n--- Job started at {now} ---')

    is_first_run = not os.path.exists(FIRST_RUN_FLAG)
    if is_first_run:
        print('First run: populating database (no Telegram, sheet will be synced after).')

    total_new = 0

    # --- MERRJEP ---
    searches = [
        {'category': 'apartamente', 'location': 'tirane',  'max_pages': 3},
        {'category': 'apartamente', 'location': 'durres',  'max_pages': 2},
        {'category': 'shtepi',      'location': 'tirane',  'max_pages': 2},
        {'category': 'apartamente', 'location': 'vlore',   'max_pages': 1},
        {'category': 'apartamente', 'location': 'shkoder', 'max_pages': 1},
    ]

    for search in searches:
        try:
            new = asyncio.run(scrape_merrjep(
                category=search['category'],
                location=search['location'],
                max_pages=search['max_pages']
            ))
            for listing in new:
                save_listing_to_sheet(listing)
                if not is_first_run:
                    send_property_notification(listing)
            total_new += len(new)
            print(f"MerrJep {search['category']} {search['location']}: {len(new)} new")
        except Exception as e:
            print(f'MerrJep error: {e}')

    # --- NJOFTIME ---
    try:
        new = scrape_njoftime(max_pages=2)
        for listing in new:
            save_listing_to_sheet(listing)
            if not is_first_run:
                send_property_notification(listing)
        total_new += len(new)
        print(f'Njoftime: {len(new)} new')
    except Exception as e:
        print(f'Njoftime error: {e}')

    # --- INSTAGRAM ---
    try:
        new = scrape_instagram(max_posts_per_tag=10)
        for listing in new:
            save_listing_to_sheet(listing)
            if not is_first_run:
                send_property_notification(listing)
        total_new += len(new)
        print(f'Instagram: {len(new)} new')
    except Exception as e:
        print(f'Instagram error: {e}')

    if is_first_run:
        open(FIRST_RUN_FLAG, 'w').close()
        print(f'--- First run done. {total_new} listings found. Syncing all to sheet... ---')
        try:
            bulk_sync_db_to_sheet(get_all_listings())
        except Exception as e:
            print(f'Bulk sync error: {e}')
    else:
        print(f'--- Done. {total_new} new listings found. ---')

if __name__ == '__main__':
    init_db()
    print('Starting Real Estate Agent — MerrJep + Njoftime + Instagram')

    # If DB already has data but sheet is empty, bulk sync now
    if os.path.exists(FIRST_RUN_FLAG):
        print('Checking if sheet needs bulk sync...')
        try:
            bulk_sync_db_to_sheet(get_all_listings())
        except Exception as e:
            print(f'Startup sync error: {e}')

    print('Running scan now...')
    run_scraper_job()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_scraper_job,
        trigger=IntervalTrigger(hours=5),
        id='property_scraper',
        replace_existing=True
    )
    print('Scanning every 5 hours. Ctrl+C to stop.')
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print('Stopped.')

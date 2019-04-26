"""
This script can be run to generate a CSV output of accounts which do not have their passwords set, along
with some useful account information, and possible explanations for the lack of password

```
python accounts_with_missing_passwords.py -o accounts.csv
```
"""
import esprit, codecs
from portality.core import app
from portality.clcsv import UnicodeWriter
from portality import models

MISSING_PASSWORD = {
    "query": {
        "filtered": {
            "query": {
                "match_all": {}
            },
            "filter": {
                "missing": {"field": "password"}
            }
        }
    }
}


def publishers_with_journals():
    """ Get accounts for all publishers with journals in the DOAJ """
    for acc in esprit.tasks.scroll(conn, 'account', q=MISSING_PASSWORD, page_size=100, keepalive='1m'):
        publisher_account = models.Account(**acc)
        journal_ids = publisher_account.journal
        if journal_ids is not None:
            for j in journal_ids:
                journal = models.Journal.pull(j)
                if journal is not None and journal.is_in_doaj():
                    yield publisher_account
                    break


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--out", help="output file path")
    args = parser.parse_args()

    if not args.out:
        print("Please specify an output file path with the -o option")
        parser.print_help()
        exit()

    conn = esprit.raw.make_connection(None, app.config["ELASTIC_SEARCH_HOST"], None, app.config["ELASTIC_SEARCH_DB"])

    with codecs.open(args.out, "wb", "utf-8") as f:
        writer = UnicodeWriter(f)
        writer.writerow(["ID", "Name", "Email", "Created", "Last Updated", "Updated Since Create?", "Has Reset Token", "Reset Token Expired?"])

        for account in publishers_with_journals():

            has_reset = account.reset_token is not None
            is_expired = account.is_reset_expired() if has_reset is True else ""

            updated_since_create = account.created_timestamp < account.last_updated_timestamp

            writer.writerow([
                account.id,
                account.name,
                account.email,
                account.created_date,
                account.last_updated,
                updated_since_create,
                has_reset,
                is_expired
            ])

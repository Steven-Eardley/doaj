import codecs
from copy import deepcopy
from datetime import datetime
from portality import clcsv
from portality.lib import normalise


## 02-27
#duplicate_report = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/duplicate_articles_global_2019-02-27.csv"
#noids_report = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/noids_2019-02-27.csv"
#log =  "/home/richard/tmp/doaj/article_duplicates_2019-02-27/log-2019-04-04.txt"
#out = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/actions-2019-04-04.csv"
#noaction = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/noaction-2019-04-04.csv"

## 04-03
duplicate_report = "/home/richard/tmp/doaj/article_duplicates_2019-04-03/duplicate_articles_global_2019-04-03.csv"
noids_report = "/home/richard/tmp/doaj/article_duplicates_2019-04-03/noids_2019-04-03.csv"
log =  "/home/richard/tmp/doaj/article_duplicates_2019-04-03/log-2019-04-04.txt"
out = "/home/richard/tmp/doaj/article_duplicates_2019-04-03/actions-2019-04-04.csv"
noaction = "/home/richard/tmp/doaj/article_duplicates_2019-04-03/noaction-2019-04-04.csv"

## testing
#duplicate_report = "/home/richard/tmp/doaj/article_duplicates_test_sheet.csv"
#noids_report = "/home/richard/tmp/doaj/article_duplicates_2019-03-29/noids_2019-03-29.csv"
#log =  "/home/richard/tmp/doaj/article_duplicates_test_sheet_log.txt"
#out = "/home/richard/tmp/doaj/article_duplicates_test_sheet_actions.csv"

INVALID_DOIS = ["undefined", "-", "http://dx.doi.org/", "http://www.gaworkshop.org/", "0", "None"]

class MatchSet(object):
    def __init__(self, typ=None):
        self._root = None
        self._matches = []
        self._notes = []

    def add_root(self, id, created, doi, fulltext, owner, issns, in_doaj, title_match):
        self._root = {
            "id" : id,
            "created": created,
            "doi" : doi,
            "fulltext" : fulltext,
            "owner" : owner,
            "issns" : issns,
            "in_doaj" : in_doaj,
            "title_match" : title_match,
            "match_type" : "self"
        }
        self._matches.append(self._root)

    def add_match(self, id, created, doi, fulltext, owner, issns, in_doaj, title_match, match_type):
        match = {
            "id" : id,
            "created": created,
            "doi" : doi,
            "fulltext" : fulltext,
            "owner" : owner,
            "issns" : issns,
            "in_doaj" : in_doaj,
            "title_match" : title_match,
            "match_type" : match_type
        }
        self._matches.append(match)

    def add_note(self, note):
        self._notes.append(note)

    def remove(self, ids):
        removes = []
        for i in range(len(self._matches)):
            if self._matches[i]["id"] in ids:
                removes.append(i)

        removes.sort(reverse=True)
        for r in removes:
            del self._matches[r]

    def contains_id(self, id):
        for m in self.matches:
            if m["id"] == id:
                return True
        return False

    def ids(self):
        return [m["id"] for m in self.matches]

    def to_rows(self):
        rows = []
        root = self.root
        matches = self.matches

        for m in matches:
            if m["id"] == root["id"]:
                continue

            # root metadata
            row = [root["id"], root["created"], root["doi"], root["fulltext"], root["owner"], root["issns"], root["in_doaj"]]
            # number of matches
            row.append(len(matches) - 1)
            # match type (currently blank)
            row.append(m["match_type"])
            # match metadata
            row += [m["id"], m["created"], m["doi"], m["fulltext"], m["owner"], m["issns"], m["in_doaj"]]
            # owner and title match
            row += ["", m["title_match"]]

            rows.append(row)

        return rows

    @property
    def matches(self):
        return self._matches

    @property
    def root(self):
        return self._root

    @property
    def notes(self):
        return self._notes


class ActionRegister(object):
    def __init__(self):
        self._actions = {}

    def set_action(self, id, action, reason):
        if id not in self._actions:
            self._actions[id] = {action : [reason]}
            return

        act = self._actions[id]
        if action not in act:
            act[action] = [reason]
            return

        act[action].append(reason)

    def has_actions(self):
        return len(self._actions) > 0

    def report(self):
        return "\n".join(
            [k + " - " + "; ".join(
                [a + " (" + "|".join(b) + ")" for a, b in v.items()]
            )
            for k, v in self._actions.items()]
        )

    def export_to(self, final_instructions):
        resolved = self.resolve()
        for r in resolved:
            if r["id"] not in final_instructions:
                final_instructions[r["id"]] = {"action" : r["action"], "reason" : r["reason"]}
            else:
                if r["action"] == "delete":
                    final_instructions[r["id"]] = {"action" : "delete", "reason" : r["reason"]}

    def resolve(self):
        resolved_actions = []
        for k, v in self._actions.items():
            resolved = {"id" : k, "action" : None, "reason" : None}
            if "delete" in v:
                resolved["action"] = "delete"
                resolved["reason"] = "; ".join(v["delete"])
            elif "remove_doi" in v and "remove_fulltext" in v:
                resolved["action"] = "delete"
                resolved["reason"] = "; ".join(v["remove_doi"]) + "|" + "; ".join("remove_fulltext")
            else:
                resolved["action"] = list(v.keys())[0]
                resolved["reason"] = "; ".join(v[resolved["action"]])
            resolved_actions.append(resolved)
        return resolved_actions


def analyse(duplicate_report, noids_report, out, noaction):

    with codecs.open(out, "wb", "utf-8") as o, \
            codecs.open(log, "wb", "utf-8") as l, \
            codecs.open(duplicate_report, "rb", "utf-8") as f, \
            codecs.open(noaction, "wb", "utf-8") as g:

        reader = clcsv.UnicodeReader(f)
        noaction_writer = clcsv.UnicodeWriter(g)
        headers = next(reader)
        noaction_writer.writerow(headers)
        noaction_writer.writerow([])

        final_instructions = {}
        next_row = None
        while True:
            match_set, next_row = _read_match_set(reader, next_row)
            ids = [m["id"] for m in match_set.matches]
            l.write("--" + str(len(ids)) + "-- " + ",".join(ids) + "\n\n")
            actions = ActionRegister()

            # get rid of any articles from the match set that are not in doaj
            _eliminate_not_in_doaj(match_set, actions)

            set_size = len(match_set.matches)
            while True:
                cont = True
                if len(match_set.matches) == 1:
                    _sanitise(match_set, actions)
                    cont = False

                if cont:
                    #_clean_doi_match_type(match_set, actions)
                    #_clean_fulltext_match_type(match_set, actions)
                    _clean_matching_dois(match_set, actions)
                    _clean_matching_fulltexts(match_set, actions)
                    _sanitise(match_set, actions)

                if len(match_set.matches) == 1:
                    cont = False

                if cont:
                    _remove_old(match_set, actions)

                if len(match_set.matches) == set_size or len(match_set.matches) == 0:
                    break
                set_size = len(match_set.matches)

            # report on the actions on this match set
            if actions.has_actions():
                l.write(actions.report())
                l.write("\n\n")

            actions.export_to(final_instructions)

            if len(match_set.matches) > 1:
                rows = match_set.to_rows()
                for row in rows:
                    noaction_writer.writerow(row)
                for note in match_set.notes:
                    noaction_writer.writerow([note])
                noaction_writer.writerow([])

            if next_row is None:
                break

        with codecs.open(noids_report, "rb", "utf-8") as n:
            nreader = clcsv.UnicodeReader(n)
            headers = next(nreader)
            for row in nreader:
                final_instructions[row[0]] = {"action" : "delete", "reason" : "no doi or fulltext"}

        writer = clcsv.UnicodeWriter(o)
        writer.writerow(["id", "action", "reason"])
        for k, v in final_instructions.items():
            writer.writerow([k, v["action"], v["reason"]])


def _remove_old(match_set, actions):
    titles = [a["title_match"] for a in match_set.matches]
    if False in titles:
        match_set.add_note("Titles do not all match")
        return

    dois = [a["doi"] for a in match_set.matches]
    doiset = set(dois)
    doi_match = len(doiset) == 1 and "" not in dois
    no_doi = len(doiset) == 0 or (len(doiset) == 1 and "" in doiset)

    fts = [a["fulltext"] for a in match_set.matches]
    ftset = set(fts)
    ft_match = len(ftset) == 1 and "" not in fts
    no_ft = len(ftset) == 0 or (len(ftset) == 1 and "" in ftset)

    # if (doi_match and ft_match) or (doi_match and no_ft) or (no_doi and ft_match):
    if doi_match or ft_match:
        dateset = []
        for a in match_set.matches:
            created = datetime.strptime(a["created"], "%Y-%m-%dT%H:%M:%SZ")
            dateset.append({"created" : created, "id" : a["id"]})

        dateset.sort(key=lambda x : x["created"])
        latest = dateset.pop()
        ids = [a["id"] for a in dateset if a["created"] != latest]
        keeping = [a["id"] for a in dateset if a["created"] == latest]
        if len(keeping) > 0:
            match_set.add_note("Some IDs have the same last updated date, can't disambiguate to remove oldest")

        match_set.remove(ids)

        for id in ids:
            if doi_match and ft_match:
                msg = "doi, fulltext and title match, and newer article available"
            elif doi_match:
                msg = "doi and title match, and newer article available"
            elif ft_match:
                msg = "fulltext and title match, and newer article available"
            else:
                msg = "error, you shouldn't be seeing this message"
            """
            if no_doi:
                msg = "no doi; fulltext and title match, and newer article available"
            elif no_ft:
                msg = "no fulltext; doi and title match, and newer article available"
            else:
                msg = "doi, fulltext and title match, and newer article available"
            """

            actions.set_action(id, "delete", msg)
    else:
        match_set.add_note("No full set of matching DOIs or Fulltexts, can't delete old versions reliably")


def _clean_matching_fulltexts(match_set, actions):
    # first find out if the match set has a complete set of dois.  If not all the records
    # have dois we can't clean the Fulltexts out.
    dois = [a["doi"] for a in match_set.matches]
    if "" in dois:
        match_set.add_note("Can't remove fulltext URLs, at least one empty string in DOI set")
        return

    # check that all the dois are unique.  If they are not, we can't remove the fulltexts
    doiset = set(dois)
    if len(dois) != len(doiset):
        match_set.add_note("Can't remove fulltext URLs, not all DOIs are unique")
        return

    # get all the Fulltexts that exist, and remember which IDs have Fulltextss
    fts = []
    has_ft = []
    for a in match_set.matches:
        if a["fulltext"] != "":
            fts.append(a["fulltext"])
            has_ft.append(a["id"])

    # check that all the fulltexts we found are the same.  If they are not, we can't remove them
    ftset = set(fts)
    if len(ftset) != 1:
        match_set.add_note("Can't remove fulltext URLs, they are not all matching")
        return

    # all the fulltext are different, and the records all have the same doi, or do not have a DOI
    for id in has_ft:
        actions.set_action(id, "remove_fulltext", "duplicated fulltext, different doi")


def _clean_matching_dois(match_set, actions):
    # first find out if the match set has a complete set of fulltexts.  If not all the records
    # have fulltexts we can't clean the DOIs out.
    fts = [a["fulltext"] for a in match_set.matches]
    if "" in fts:
        match_set.add_note("Can't remove DOIs, at least one empty string in Fulltext set")
        return

    # check that all the fulltexts are unique.  If they are not, we can't remove the DOIs
    ftset = set(fts)
    if len(fts) != len(ftset):
        match_set.add_note("Can't remove DOIs, not all Fulltexts are unique")
        return

    # get all the DOIs that exist, and remember which IDs have DOIs
    dois = []
    has_doi = []
    for a in match_set.matches:
        if a["doi"] != "":
            dois.append(a["doi"])
            has_doi.append(a["id"])

    # check that all the dois we found are the same.  If they are not, we can't remove them
    doiset = set(dois)
    if len(doiset) != 1:
        match_set.add_note("Can't remove DOIs, they are not all matching")
        return

    # all the fulltext are different, and the records all have the same doi, or do not have a DOI
    for id in has_doi:
        actions.set_action(id, "remove_doi", "duplicated doi, different fulltexts")


def _sanitise(match_set, actions):
    removes = []
    for article in match_set.matches:
        if article["doi"] in INVALID_DOIS:
            if article["fulltext"] == "":
                removes.append(article["id"])
                actions.set_action(article["id"], "delete", "invalid doi, and no fulltext")
            else:
                actions.set_action(article["id"], "remove_doi", "invalid doi")

    if len(removes) > 0:
        match_set.remove(removes)


def _eliminate_not_in_doaj(match_set, actions):
    removes = []
    for i in range(len(match_set.matches)):
        article = match_set.matches[i]
        if not article["in_doaj"]:
            removes.append(article["id"])

    if len(removes) > 0:
        match_set.remove(removes)
        match_set.add_note("not in DOAJ: " + ", ".join(removes))
        for r in removes:
            actions.set_action(r, "delete", "not in doaj")
    else:
        match_set.add_note("All matches in DOAJ")


def _read_match_set(reader, next_row):
    n_matches = -1
    match_set = MatchSet()
    while True:
        if next_row is not None:
            row = deepcopy(next_row)
            next_row = None
        else:
            try:
                row = next(reader)
            except StopIteration:
                return match_set, None

        if row is None:
            return match_set, None

        a_id = row[0]
        root = match_set.root
        if root is not None and a_id != root["id"]:
            return match_set, row

        a_created = row[1]
        try:
            a_doi = normalise.normalise_doi(row[2])
        except:
            a_doi = row[2]
        try:
            a_ft = normalise.normalise_url(row[3])
        except:
            a_ft = row[3]
        a_owner = row[4]
        a_issns = row[5]
        a_in_doaj = row[6] == "True"

        if n_matches != -1:
            n_matches = int(row[7])

        match_type = row[8]

        b_id = row[9]
        b_created = row[10]
        try:
            b_doi = normalise.normalise_doi(row[11])
        except:
            b_doi = row[11]
        try:
            b_ft = normalise.normalise_url(row[12])
        except:
            b_ft = row[12]
        b_owner = row[13]
        b_issns = row[14]
        b_in_doaj = row[15] == "True"

        title_match = row[17] == "True"

        if root is None:
            match_set.add_root(a_id, a_created, a_doi, a_ft, a_owner, a_issns, a_in_doaj, title_match)

        match_set.add_match(b_id, b_created, b_doi, b_ft, b_owner, b_issns, b_in_doaj, title_match, match_type)

    # a catch to make sure that everything is ok with the match set detection
    assert n_matches + 1 == len(match_set.matches)

def compare_outputs(duplicate_report):
    original = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/actions-2019-04-02.csv"
    compare = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/actions-2019-04-04.csv"
    missing_out = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/missing.csv"
    extra_out = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/extra.csv"
    reference = "/home/richard/tmp/doaj/article_duplicates_2019-02-27/reference.csv"

    with codecs.open(original, "rb", "utf-8") as f1:
        r1 = clcsv.UnicodeReader(f1)
        next(r1)
        id1 = [x[0] for x in r1]

    with codecs.open(compare, "rb", "utf-8") as f2:
        r2 = clcsv.UnicodeReader(f2)
        next(r2)
        id2 = [x[0] for x in r2]

    missing = [x for x in id1 if x not in id2]
    print(("missing {x}".format(x=len(missing))))
    with codecs.open(missing_out, "wb", "utf-8") as f3:
        f3.write("\n".join(missing))

    extra = [x for x in id2 if x not in id1]
    print(("extra {x}".format(x=len(extra))))
    with codecs.open(extra_out, "wb", "utf-8") as f4:
        f4.write("\n".join(extra))

    with codecs.open(duplicate_report, "rb", "utf-8") as f5, \
            codecs.open(reference, "wb", "utf-8") as f6:
        r5 = clcsv.UnicodeReader(f5)
        w6 = clcsv.UnicodeWriter(f6)
        headers = next(r5)
        w6.writerow(headers)
        w6.writerow([])

        seen_roots = []
        next_row = None
        while True:
            match_set, next_row = _read_match_set(r5, next_row)
            for m in missing:
                if match_set.contains_id(m):
                    root_id = match_set.root["id"]
                    if root_id in seen_roots:
                        continue
                    seen_roots.append(root_id)

                    print(("Reference set for root id {x}".format(x=root_id)))
                    rows = match_set.to_rows()
                    for row in rows:
                        w6.writerow(row)
                    w6.writerow([])

            if next_row is None:
                break


analyse(duplicate_report, noids_report, out, noaction)
#compare_outputs(duplicate_report)
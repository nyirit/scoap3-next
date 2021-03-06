import logging
from collections import Counter

from flask import current_app
from inspire_utils.record import get_value
from invenio_search import current_search_client

from scoap3.modules.records.util import get_first_journal, get_first_doi, get_arxiv_primary_category
from scoap3.utils.arxiv import get_clean_arXiv_id


logger = logging.getLogger(__name__)


def get_query_string(**kwargs):
    """
    Concatenates the non-None keyword arguments to create a query string for ElasticSearch.

    :return: concatenated query string or None if not arguments were given
    """
    q = ['%s:%s' % (key, value) for key, value in kwargs.items() if value not in (None, '')]
    return ' AND '.join(q) or None


def affiliations_export(country=None, year=None):
    """
    Creates affiliation data filtered by country and year.

    :param country: only affiliations for this country will be included. If None, all countries are included.
    :param year: only articles *published* in this year will be included. If None, all articles are included.
    """

    size = current_app.config.get('TOOL_ELASTICSEARCH_PAGE_SIZE', 100)
    search_index = current_app.config.get('SEARCH_UI_SEARCH_INDEX')
    source_fields = [
        'publication_info.year', 'publication_info.journal_title', 'arxiv_eprints', 'dois', 'authors', 'control_number',
    ]
    query = get_query_string(country=country, year=year)

    result_data = []
    index = 0
    total_hits = None
    while total_hits is None or index < total_hits:
        # query ElasticSearch for result
        search_results = current_search_client.search(q=query, index=search_index, _source=source_fields,
                                                      size=size, from_=index)
        total_hits = search_results['hits']['total']
        index += len(search_results['hits']['hits'])

        # extract and add data to result list
        for hit in search_results['hits']['hits']:
            record = hit['_source']

            year = record['publication_info'][0]['year']
            journal = get_first_journal(record)
            doi = get_first_doi(record)
            arxiv = get_clean_arXiv_id(record)
            arxiv_category = get_arxiv_primary_category(record)

            authors = record.get('authors', ())
            total_authors = len(authors)

            extracted_affiliations = Counter()
            for author in authors:
                # if there are no affiliations, we cannot add this author
                # (this also means the record is not valid according to the schema)
                if 'affiliations' not in author:
                    logger.warn('No affiliations for author. doi=%s' % doi)
                    continue

                # aggregate affiliations
                for aff in author['affiliations']:
                    aff_country = aff.get('country', 'UNKNOWN')
                    if country in (None, '') or aff_country == country:
                        value = ((aff['value'], aff_country), )
                        extracted_affiliations.update(value)

            if not extracted_affiliations:
                logger.warn('No extracted affiliations for article. doi=%s' % doi)

            # add extracted information to result list
            for meta, count in extracted_affiliations.items():
                aff_value, aff_country = meta
                result_data.append(
                    [year, journal, doi, arxiv, arxiv_category, aff_country, aff_value, count, total_authors]
                )

    return {
        'header': ['year', 'journal', 'doi', 'arxiv number', 'primary arxiv category', 'country', 'affiliation',
                   'authors with affiliation', 'total number of authors'],
        'data': result_data
    }


def authors_export(country=None, year=None):
    """
    Creates author and affiliation data filtered by country and year.

    :param country: only affiliations for this country will be included. If None, all countries are included.
    :param year: only articles *published* in this year will be included. If None, all articles are included.
    """

    size = current_app.config.get('TOOL_ELASTICSEARCH_PAGE_SIZE', 100)
    search_index = current_app.config.get('SEARCH_UI_SEARCH_INDEX')
    source_fields = [
        'publication_info.year', 'publication_info.journal_title', 'arxiv_eprints', 'dois', 'authors', 'control_number',
    ]
    query = get_query_string(country=country, year=year)

    result_data = []
    index = 0
    total_hits = None
    while total_hits is None or index < total_hits:
        # query ElasticSearch for result
        search_results = current_search_client.search(q=query, index=search_index, _source=source_fields,
                                                      size=size, from_=index)
        total_hits = search_results['hits']['total']
        index += len(search_results['hits']['hits'])

        # extract and add data to result list
        for hit in search_results['hits']['hits']:
            record = hit['_source']

            year = record['publication_info'][0]['year']
            journal = get_first_journal(record)
            doi = get_first_doi(record)
            arxiv = get_clean_arXiv_id(record)
            arxiv_category = get_arxiv_primary_category(record)

            authors = record.get('authors', ())
            total_authors = len(authors)

            for author in authors:
                # if there are no affiliations, we cannot add this author
                # (this also means the record is not valid according to the schema)
                if 'affiliations' not in author:
                    logger.warn('No affiliations for author. doi=%s' % doi)
                    continue

                author_name = author.get('full_name', 'UNKNOWN')
                # add extracted information to result list
                for affiliation in author['affiliations']:
                    aff_country = affiliation.get('country', 'UNKNOWN')
                    aff_value = affiliation['value']
                    result_data.append(
                        [year, journal, doi, arxiv, arxiv_category, author_name, aff_country, aff_value, total_authors]
                    )

    return {
        'header': ['year', 'journal', 'doi', 'arxiv number', 'primary arxiv category', 'author', 'country',
                   'affiliation', 'total number of authors'],
        'data': result_data
    }


def search_export(es_dict):
    """
    Exports basic record data for all filtered records.

    :param es_dict: defines the ElasticSearch data in order to filter the records.
    """

    fields = current_app.config.get('SEARCH_EXPORT_FIELDS')
    source_fields = [field for _, field, _ in fields]

    size = current_app.config.get('TOOL_ELASTICSEARCH_PAGE_SIZE', 100)
    search_index = current_app.config.get('SEARCH_UI_SEARCH_INDEX')

    result_data = []
    index = 0
    total_hits = None
    while total_hits is None or index < total_hits:
        # query ElasticSearch for result
        search_results = current_search_client.search(body=es_dict, index=search_index, _source=source_fields,
                                                      size=size, from_=index)
        total_hits = search_results['hits']['total']
        index += len(search_results['hits']['hits'])

        # extract and add data to result list
        for hit in search_results['hits']['hits']:
            record = hit['_source']
            result_data.append([get_value(record, key, '') for _, _, key in fields])

    return {
        'header': [name for name, _, _ in fields],
        'data': result_data
    }

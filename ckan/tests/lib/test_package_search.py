import time

from ckan.model import Package
from ckan.lib.search import make_search, SearchOptions
import ckan.model as model
from ckan.tests import *
from ckan.lib.create_test_data import CreateTestData

class TestSearch(TestController):
    q_all = u'penguin'

    @classmethod
    def setup_class(self):
        indexer = TestSearchIndexer()
        model.Session.remove()
        CreateTestData.create_search_test_data()

        # now remove a tag so we can test search with deleted tags
        model.repo.new_revision()
        gils = model.Package.by_name(u'gils')
        # an existing tag used only by gils
        self.tagname = u'registry'
        # we aren't guaranteed it is last ...
        idx = [ t.name for t in gils.tags].index(self.tagname)
        del gils.tags[idx]
        model.repo.commit_and_remove()
        indexer.index()

        self.gils = model.Package.by_name(u'gils')
        self.war = model.Package.by_name(u'warandpeace')
        self.russian = model.Tag.by_name(u'russian')
        self.tolstoy = model.Tag.by_name(u'tolstoy')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def _pkg_names(self, result):
        return ' '.join(result['results'])

    def _check_entity_names(self, result, names_in_result):
        names = result['results']
        for name in names_in_result:
            if name not in names:
                return False
        return True

    # Can't search for all records in postgres, so search for 'penguin' which
    # we have put in all the records.
    def test_1_all_records(self):
        # all records
        result = make_search().search(self.q_all)
        assert 'gils' in result['results'], result['results']
        assert result['count'] > 5, result['count']

    def test_1_name(self):
        # exact name
        result = make_search().search(u'gils')
        assert self._pkg_names(result) == 'gils', result
        assert result['count'] == 1, result

# Can't search for partial words in postgres
##    def test_1_name_partial(self):
##        # partial name
##        result = make_search().search(u'gil')
##        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
##        assert result['count'] == 1, self._pkg_names(result)

    def test_1_name_multiple_results(self):
        result = make_search().search(u'gov')
        assert self._check_entity_names(result, ('us-gov-images', 'usa-courts-gov')), self._pkg_names(result)
        assert result['count'] == 4, self._pkg_names(result)

    def test_1_name_token(self):
        result = make_search().search(u'name:gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)

        result = make_search().search(u'title:gils')
        assert not self._check_entity_names(result, ('gils')), self._pkg_names(result)

    def test_2_title(self):
        # exact title, one word
        result = make_search().search(u'Opengov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

##        # part word
##        result = Search().search(u'gov.se')
##        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # multiple words
        result = make_search().search(u'Government Expenditure')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words wrong order
        result = make_search().search(u'Expenditure Government')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words, one doesn't match
        result = make_search().search(u'Expenditure Government China')
        assert self._pkg_names(result) == '', self._pkg_names(result)

# Quotation not supported now
##        # multiple words quoted
##        result = Search().search(u'"Government Expenditure"')
##        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

##        # multiple words quoted wrong order
##        result = Search().search(u'Expenditure Government')
##        assert self._pkg_names(result) == '', self._pkg_names(result)

        # token
        result = make_search().search(u'title:Opengov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # token
        result = make_search().search(u'title:gils')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        # token
        result = make_search().search(u'randomthing')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_field(self):
        result = make_search().search(u'country-sweden')
        assert self._check_entity_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)

    def test_tags_token_simple(self):
        result = make_search().search(u'tags:country-sweden')
        assert self._check_entity_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)

        result = make_search().search(u'tags:wildlife')
        assert self._pkg_names(result) == 'us-gov-images', self._pkg_names(result)

    def test_tags_token_simple_with_deleted_tag(self):
        # registry has been deleted
        result = make_search().search(u'tags:registry')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_token_multiple(self):
        result = make_search().search(u'tags:country-sweden tags:format-pdf')
        assert self._pkg_names(result) == 'se-publications', self._pkg_names(result)

    def test_tags_token_complicated(self):
        result = make_search().search(u'tags:country-sweden tags:somethingrandom')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_token_blank(self):
        options = SearchOptions({'q':u'tags: wildlife'})
        result = make_search().run(options)
        assert self._pkg_names(result) == 'us-gov-images', self._pkg_names(result)

    def test_tag_basic(self):
        options = SearchOptions({'q':u'gov',
                                 'entity':'tag'})
        result = make_search().run(options)
        assert result['count'] == 2, result
        assert self._check_entity_names(result, ('gov', 'government')), self._pkg_names(result)

    def test_tag_basic_2(self):
        options = SearchOptions({'q':u'wildlife',
                                 'entity':'tag'})
        result = make_search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_tag_with_tags_option(self):
        options = SearchOptions({'q':u'tags:wildlife',
                                 'entity':'tag'})
        result = make_search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_tag_with_blank_tags(self):
        options = SearchOptions({'q':u'tags: wildlife',
                                 'entity':'tag'})
        result = make_search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_pagination(self):
        # large search
        all_results = make_search().search(self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # limit
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        result = make_search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        assert count == all_pkg_count
        assert pkgs == all_pkgs[:2]

        # offset
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        options.offset = 2
        results = make_search().run(options)
        pkgs = results['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[2:4]

        # larger offset
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        options.offset = 4
        result = make_search().run(options)
        pkgs = result['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[4:6]

    def test_order_by(self):
        # large search
        all_results = make_search().search(self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # rank
        options = SearchOptions({'q':u'penguin'})
        options.order_by = 'rank'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        assert fields[0] == 'usa-courts-gov', fields # has penguin three times
        assert pkgs == all_pkgs, pkgs #default ordering        

        # name
        options = SearchOptions({'q':self.q_all})
        options.order_by = 'name'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # title
        options = SearchOptions({'q':self.q_all})
        options.order_by = 'title'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).title for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # notes
        options = SearchOptions({'q':self.q_all})
        options.order_by = 'notes'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).notes for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # extra field
## TODO: Get this working
##        options = SearchOptions({'q':self.q_all})
##        options.order_by = 'date_released'
##        result = Search().run(options)
##        pkgs = result['results']
##        fields = [model.Package.by_name(pkg_name).extras.get('date_released') for pkg_name in pkgs]
##        sorted_fields = fields; sorted_fields.sort()
##        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

    def test_search_notes_on(self):
        options = SearchOptions({'q':u'restrictions'})
        result = make_search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        
    def test_search_foreign_chars(self):
        result = make_search().search('umlaut')
        assert result['results'] == ['gils'], result['results']
        result = make_search().search(u'thumb')
        assert result['count'] == 0, result['results']
        result = make_search().search(u'th\xfcmb')
        assert result['results'] == ['gils'], result['results']

    # Groups searching deprecated for now
    def _test_groups(self):
        result = make_search().search(u'groups:random')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        result = make_search().search(u'groups:ukgov')
        assert result['count'] == 4, self._pkg_names(result)

        result = make_search().search(u'groups:ukgov tags:us')
        assert result['count'] == 2, self._pkg_names(result)

    def test_query(self):
        options = SearchOptions({'q':u'tags: wildlife'})
        run_result = make_search().run(options)
        query = make_search().query(options)
        assert query.count() == run_result['count']
        assert query.first()[0].name == run_result['results'][0], '%s\n%s' % (query.first()[0].name, run_result['results'][0])
        

class TestSearchOverall(TestController):
    @classmethod
    def setup_class(self):
        indexer = TestSearchIndexer()
        CreateTestData.create()
        indexer.index()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def _check_search_results(self, terms, expected_count, expected_packages=[], only_open=False, only_downloadable=False):
        options = SearchOptions({'q':unicode(terms)})
        options.filter_by_openness = only_open
        options.filter_by_downloadable = only_downloadable
        result = make_search().run(options)
        pkgs = result['results']
        count = result['count']
        assert count == expected_count, (count, expected_count)
        for expected_pkg in expected_packages:
            assert expected_pkg in pkgs, '%s : %s' % (expected_pkg, result)

    def test_overall(self):
        self._check_search_results('annakarenina', 1, ['annakarenina'] )
        self._check_search_results('warandpeace', 1, ['warandpeace'] )
        self._check_search_results('', 0 )
        self._check_search_results('A Novel By Tolstoy', 1, ['annakarenina'] )
        self._check_search_results('title:Novel', 1, ['annakarenina'] )
        self._check_search_results('title:peace', 0 )
        self._check_search_results('name:warandpeace', 1 )
        self._check_search_results('groups:david', 2 )
        self._check_search_results('groups:roger', 1 )
        self._check_search_results('groups:lenny', 0 )
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, False )
        self._check_search_results('annakarenina', 1, ['annakarenina'], False, True )
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, True )
        

class TestGeographicCoverage(TestController):
    @classmethod
    def setup_class(self):
        indexer = TestSearchIndexer()
        init_data = [
            {'name':'eng',
             'extras':{'geographic_coverage':'100000: England'},},
            {'name':'eng_ni',
             'extras':{'geographic_coverage':'100100: England, Northern Ireland'},},
            {'name':'uk',
             'extras':{'geographic_coverage':'111100: United Kingdom (England, Scotland, Wales, Northern Ireland'},},
            {'name':'gb',
             'extras':{'geographic_coverage':'111000: Great Britain (England, Scotland, Wales)'},},
            {'name':'none',
             'extras':{'geographic_coverage':'000000:'},},
            ]
        CreateTestData.create_arbitrary(init_data)
        indexer.index()


    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
    
    def _do_search(self, q, expected_pkgs, count=None):
        options = SearchOptions({'q':q})
        options.order_by = 'rank'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def _filtered_search(self, value, expected_pkgs, count=None):
        options = SearchOptions({'q':'', 'geographic_coverage':value})
        options.order_by = 'rank'
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search(u'england', ['eng', 'eng_ni', 'uk', 'gb'], 4)
        self._do_search(u'northern ireland', ['eng_ni', 'uk'], 2)
        self._do_search(u'united kingdom', ['uk'], 1)
        self._do_search(u'great britain', ['gb'], 1)

    def test_1_filtered(self):
        self._filtered_search(u'england', ['eng', 'eng_ni', 'uk', 'gb'], 4)

class TestExtraFields(TestController):
    @classmethod
    def setup_class(self):
        indexer = TestSearchIndexer()
        init_data = [
            {'name':'a',
             'extras':{'department':'abc',
                       'agency':'ag-a'},},
            {'name':'b',
             'extras':{'department':'bcd',
                       'agency':'ag-b'},},
            {'name':'c',
             'extras':{'department':'cde abc'},},
            {'name':'none',
             'extras':{'department':''},},
            ]
        CreateTestData.create_arbitrary(init_data)
        indexer.index()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
    
    def _do_search(self, department, expected_pkgs, count=None):
        options = SearchOptions({'q':''})
        options.department = department
        result = make_search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search(u'bcd', 'b', 1)
        self._do_search(u'abc', ['a', 'c'], 2)
        self._do_search(u'cde', 'c', 1)
        self._do_search(u'abc cde', [], 0)
        self._do_search(u'cde abc', 'c', 1)

class TestRank(TestController):
    @classmethod
    def setup_class(self):
        self.purge_all_packages()
        indexer = TestSearchIndexer()

        init_data = [{'name':u'test1-penguin-canary',
                      'tags':u'canary goose squirrel wombat wombat'},
                     {'name':u'test2-squirrel-squirrel-canary-goose',
                      'tags':u'penguin wombat'},
                     ]
        CreateTestData.create_arbitrary(init_data)
        indexer.index()
        self.pkg_names = [u'test1-penguin-canary',
                     u'test2-squirrel-squirrel-canary-goose']

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()
    
    def _do_search(self, q, wanted_results):
        options = SearchOptions({'q':q})
        options.order_by = 'rank'
        result = make_search().run(options)
        results = result['results']
        err = 'Wanted %r, got %r' % (wanted_results, results)
        print wanted_results, results
        assert wanted_results[0] == results[0], err
        assert wanted_results[1] == results[1], err

    def test_0_basic(self):
        self._do_search(u'wombat', self.pkg_names)
        self._do_search(u'squirrel', self.pkg_names[::-1])
        self._do_search(u'canary', self.pkg_names)

    def test_1_weighting(self):
        self._do_search(u'penguin', self.pkg_names)
        self._do_search(u'goose', self.pkg_names[::-1])

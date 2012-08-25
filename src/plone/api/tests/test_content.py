# -*- coding: utf-8 -*-
"""Tests for plone.api content."""
import mock
import unittest
import pkg_resources
from Acquisition import aq_base

try:
    pkg_resources.get_distribution('plone.dexterity')
except pkg_resources.DistributionNotFound:
    HAS_DEXTERITY = False
    pass
else:
    HAS_DEXTERITY = True

from plone import api
from plone.api.tests.base import INTEGRATION_TESTING


class TestPloneApiContent(unittest.TestCase):
    """Unit tests for content manipulation using plone.api"""

    layer = INTEGRATION_TESTING

    def setUp(self):
        """  Create a portal structure which we can test against:
        Plone (portal root)
        |-- blog
        |-- about
        |   |-- team
        |   `-- contact
        `-- events
            |-- training
            |-- conference
            `-- sprint

        """
        self.portal = self.layer['portal']
        self.portal.manage_delObjects(
            [x.id for x in self.portal.getFolderContents()])  # Clean up

        self.blog = api.content.create(
            type='Link', id='blog', container=self.portal)
        self.about = api.content.create(
            type='Folder', id='about', container=self.portal)
        self.events = api.content.create(
            type='Folder', id='events', container=self.portal)

        self.team = api.content.create(
            container=self.about, type='Document', id='team')
        self.contact = api.content.create(
            container=self.about, type='Document', id='contact')

        self.training = api.content.create(
            container=self.events, type='Event', id='training')
        self.conference = api.content.create(
            container=self.events, type='Event', id='conference')
        self.sprint = api.content.create(
            container=self.events, type='Event', id='sprint')

    def test_create_constraints(self):
        """ Test the constraints when creating content """

        # This will definitely fail
        self.assertRaises(api.exceptions.MissingParameterError, api.content.create)

        # Check the contraints for the type container
        self.assertRaises(
            api.exceptions.MissingParameterError, api.content.create, type='Document', id='test-doc')

        # Check the contraints for the type parameter
        container = mock.Mock()
        self.assertRaises(
            api.exceptions.MissingParameterError, api.content.create, container=container, id='test-doc')

        # Check the contraints for id and title parameters
        self.assertRaises(
            api.exceptions.MissingParameterError,
            api.content.create,
            container=container, type='Document'
        )

        # Check the contraints for allowed types in the container
        container = self.events
        self.assertRaises(
            api.exceptions.InvalidParameterError,
            api.content.create,
            container=container,
            type='foo',
            id='test-foo'
        )

        # Check the contraints for allowed types in the container if the container is the portal
        container = self.portal
        self.assertRaises(
            api.exceptions.InvalidParameterError,
            api.content.create,
            container=container,
            type='foo',
            id='test-foo'
        )

        # Check the contraints for allowed types in the container
        # Create a folder
        folder = api.content.create(
            container=container, type='Folder', id='test-folder')
        assert folder
        # Constraint the allowed types
        folder.setConstrainTypesMode(1)
        folder.setLocallyAllowedTypes(('News Item',))
        self.assertRaises(
            api.exceptions.InvalidParameterError,
            api.content.create,
            container=folder,
            type='Document',
            id='test-doc'
        )

    @unittest.skipUnless(HAS_DEXTERITY, "Only run when Dexterity is available.")
    def test_create_dexterity(self):
        """ Test create content based on Dexterity """
        raise NotImplemented

    def test_create_archetypes(self):
        """ Test creating content based on Archetypes """

        container = self.portal

        # Create a folder
        folder = api.content.create(
            container=container, type='Folder', id='test-folder')
        assert folder
        self.assertEqual(folder.id, 'test-folder')
        self.assertEqual(folder.portal_type, 'Folder')

        # Create a document
        page = api.content.create(
            container=folder, type='Document', id='test-document')
        assert page
        self.assertEqual(page.id, 'test-document')
        self.assertEqual(page.portal_type, 'Document')

        # Create a document with a title and without an id
        page = api.content.create(
            container=folder, type='Document', title='Test id generated')
        assert page
        self.assertEqual(page.id, 'test-id-generated')
        self.assertEqual(page.Title(), 'Test id generated')
        self.assertEqual(page.portal_type, 'Document')

        # Try to create another page, this should fail because of strict mode
        self.assertRaises(
            api.exceptions.InvalidParameterError, api.content.create,
            container=folder, type='Document', id='test-document'
        )

    def test_create_non_strict(self):
        """" Test the content creating without strict mode. """
        container = self.portal

        first_page = api.content.create(
            container=container, type='Document', id='test-document',
            strict=False)
        assert first_page
        self.assertEqual(first_page.id, 'test-document')
        self.assertEqual(first_page.portal_type, 'Document')

        # Second page is created with non-conflicting id
        second_page = api.content.create(
            container=container, type='Document', id='test-document',
            strict=False)
        assert second_page
        self.assertEqual(second_page.id, 'test-document-1')
        self.assertEqual(second_page.portal_type, 'Document')

    def test_get_constraints(self):
        """ Test the constraints when content is fetched with get """

        # Path and UID parameter can not be given together
        self.assertRaises(ValueError, api.content.get, path='/', UID='dummy')

        # Either a path or UID must be given
        self.assertRaises(ValueError, api.content.get)

    def test_get(self):
        """ Test the getting of content. Create a simple structure with
        a folder which contains a document
        """

        # Test getting the about folder by path and UID
        about_by_path = api.content.get('/about')
        about_by_uid = api.content.get(UID=self.about.UID())
        self.assertEqual(self.about, about_by_path)
        self.assertEqual(self.about, about_by_uid)

        # Test getting the team document by path and UID
        team_by_path = api.content.get('/about/team')
        team_by_uid = api.content.get(UID=self.team.UID())
        self.assertEqual(self.team, team_by_path)
        self.assertEqual(self.team, team_by_uid)

        # Test getting the team document by path that has portal id included
        team_by_path = api.content.get(
            '/{0}/about/team'.format(self.portal.getId()))
        self.assertEqual(self.team, team_by_path)

        # Test getting an non-existing item by path and UID
        self.assertFalse(api.content.get('/spam/ham'))
        self.assertFalse(api.content.get(UID='bacon'))

    def test_move_constraints(self):
        """ Test the constraints for moving content """

        # When no parameters are given an error is raised
        self.assertRaises(ValueError, api.content.move)

        container = mock.Mock()
        # Source is missing an should raise an error
        self.assertRaises(ValueError, api.content.move, source=container)
        # Target is missing an should raise an error
        self.assertRaises(ValueError, api.content.move, target=container)

    def test_move(self):
        """ Test moving of content """

        container = self.portal

        # Move contact to the same folder (basically a rename)
        api.content.move(source=self.contact, id='nu-contact')
        assert container['about']['nu-contact']
        assert 'contact' not in container['about'].keys()

        # Move team page to portal root
        api.content.move(source=self.team, target=container)
        assert container['team']
        assert 'team' not in container['about'].keys()

        # When moving objects we can change the id
        team = container['team']
        api.content.move(source=team, target=self.about, id='our-team')
        assert container['about']['our-team']
        assert 'team' not in container.keys()

        # Test with strict parameter disabled when moving content
        api.content.create(
            container=self.about, type='Link', id='link-to-blog')
        api.content.move(
            source=self.blog, target=self.about, id='link-to-blog',
            strict=False)
        assert container['about']['link-to-blog-1']
        assert 'link-to-blog' not in container.keys()

        api.content.move(source=self.conference, id='conference-renamed')
        self.assertEqual(self.conference.id, 'conference-renamed')

    def test_copy_constraints(self):
        """ Test the constraints for moving content """

        # When no parameters are given an error is raised
        self.assertRaises(ValueError, api.content.copy)

        container = mock.Mock()
        # Source is missing an should raise an error
        self.assertRaises(ValueError, api.content.copy, source=container)
        # Target is missing an should raise an error
        self.assertRaises(ValueError, api.content.copy, target=container)

    def test_copy(self):
        """ Test the copying of content """

        container = self.portal

        # Copy team page to portal root
        api.content.copy(source=self.team, target=container)
        assert container['team']  # Content has moved to portal root
        self.assertRaises(KeyError, container['about']['team'])

        # When moving objects we can change the id
        api.content.copy(source=self.team, target=self.about, id='our-team')
        assert container['about']['our-team']
        self.assertRaises(KeyError, container['team'])

        # Test the strict parameter disabled when moving content
        api.content.create(
            container=self.about, type='Link', id='link-to-blog')

        api.content.copy(
            source=self.blog, target=self.about, id='link-to-blog',
            strict=False)
        assert container['about']['link-to-blog-1']
        self.assertRaises(KeyError, container['blog'])

    def test_delete_constraints(self):
        """ Test the constraints for deleting content """

        # When no parameters are given an error is raised
        self.assertRaises(ValueError, api.content.delete)

    def test_delete(self):
        """ Test deleting a content item """

        container = self.portal

        # The content item must be given as parameter
        self.assertRaises(ValueError, api.content.delete)

        # Delete the contact page
        api.content.delete(self.contact)
        assert 'contact' not in container['about'].keys()

    def test_get_state(self):
        """ Test retrieving the workflow state of a content item """

        # This should fail because an content item is mandatory
        self.assertRaises(ValueError, api.content.get_state)

        review_state = api.content.get_state(obj=self.blog)
        self.assertEqual(review_state, 'private')

    def test_transition(self):
        """ Test transitioning the workflow state on a content item"""

        self.assertRaises(ValueError, api.content.transition)
        self.assertRaises(ValueError, api.content.transition, obj=mock.Mock())
        self.assertRaises(
            ValueError, api.content.transition, transition='publish')

        api.content.transition(obj=self.blog, transition='publish')
        review_state = api.content.get_state(obj=self.blog)
        self.assertEqual(review_state, 'published')

    def test_get_view_constraints(self):
        """ Test the constraints for deleting content """
        request = self.layer['request']

        # When no parameters are given an error is raised
        self.assertRaises(api.exceptions.MissingParameterError, api.content.get_view)

        # name is required
        self.assertRaises(
            api.exceptions.MissingParameterError,
            api.content.get_view,
            context=self.blog,
            request=request
        )

        # context is required
        self.assertRaises(
            api.exceptions.MissingParameterError,
            api.content.get_view,
            name='plone',
            request=request
        )

        # request is required
        self.assertRaises(
            api.exceptions.MissingParameterError,
            api.content.get_view,
            name='plone',
            context=self.blog
        )

    def test_get_view(self):
        """ Test the view """
        request = self.layer['request']

        view = api.content.get_view(
            name='plone',
            context=self.blog,
            request=request
        )
        self.assertEqual(aq_base(view.context), aq_base(self.blog))
        self.assertEqual(view.__name__, 'plone')
        self.assertTrue(hasattr(view, 'getIcon'))
        self.assertEqual(request['ACTUAL_URL'], 'http://nohost')

        # Try another standard view.
        view = api.content.get_view(
            name='plone_context_state',
            context=self.blog,
            request=request
        )
        self.assertEqual(view.__name__, 'plone_context_state')
        self.assertEqual(aq_base(view.canonical_object()), aq_base(self.blog))

    def test_get_view_view_not_found(self):
        """Test that error msg lists available views if a view is not found."""
        request = self.layer['request']

        with self.assertRaises(api.exceptions.InvalidParameterError) as cm:
            api.content.get_view(name='foo',
                                 context=self.blog,
                                 request=request)

        self.maxDiff = None  # to see assert diff
        self.assertMultiLineEqual(
            cm.exception.message,
            "Cannot find a view with name 'foo'. \n"
            "Available views are:\n"
            '\n'
            'zptviews.html\n'
            'p.a.jqt.testPage\n'
            'cutObject\n'
            'display_query_results\n'
            'images\n'
            'tinymce-save\n'
            'at_textarea_widget\n'
            'plone_nextprevious_view\n'
            'plone_contentrules_info\n'
            'at_base_edit_view\n'
            'default_page\n'
            'plone.contentmenu.display\n'
            'kukittestsuite\n'
            'skin\n'
            'changeViewTemplate\n'
            'link_renderer\n'
            'archetypes-querywidget-relativedatewidget\n'
            'portal_tabs_view\n'
            'convert-legacy-portlets\n'
            'reviewlist_update_table\n'
            'kss_view\n'
            'resolveuid_and_caption\n'
            'refbrowser_querycatalog\n'
            'changeWorkflowState\n'
            'replaceMacro\n'
            'manage_interfaces\n'
            'tinymce-jsonconfiguration\n'
            'blob-maintenance\n'
            'refreshPortlet\n'
            'archetypes-querywidget-multipleselectionwidget\n'
            'resolveuid\n'
            'pas_member\n'
            'at_lifecycle_view\n'
            'navtree_builder_view\n'
            'calendar_widget\n'
            'querybuilderjsonconfig\n'
            'kss_devel_mode\n'
            'contenthistory\n'
            'resourceregistries_styles_view\n'
            'plone_javascript_variables.js\n'
            'pas_search\n'
            'sharing\n'
            'inlineDeletePortlet\n'
            'manage-viewlets\n'
            'historyview\n'
            'replaceRulesTable\n'
            'plone_context_state\n'
            'plone_tools\n'
            'authenticator\n'
            'widget_macros\n'
            'edit-markers.html\n'
            'kssValidateField\n'
            'archetypes-querywidget-relativepathwidget\n'
            'at_selection_widget\n'
            'sitemap_view\n'
            'resourceregistries_scripts_view\n'
            'resourceregistries_kss_view\n'
            'contextportlets\n'
            'kss_field_decorator_view\n'
            'querybuilderresults\n'
            'manage-portlets\n'
            'resource\n'
            'migrate-btrees\n'
            'tinymce-upload\n'
            'addform_macros\n'
            'uuid\n'
            'plone_redirector_view\n'
            'date_components_support\n'
            'replaceInnerByMacro\n'
            'sitemap_builder_view\n'
            'archetypes-querywidget-stringwidget\n'
            'plone.contentmenu.actions\n'
            'form_macros\n'
            'plone_layout\n'
            'base-pageform.html\n'
            'folder_contents\n'
            'standard_macros\n'
            'view\n'
            'tinymce-jsonlinkablesearch\n'
            'savekupu\n'
            'replaceByMacro\n'
            'tinymce-setDescription\n'
            'contenthistorypopup\n'
            'tinymce-jsondetails\n'
            'datepickerconfig\n'
            'kss_formlib_inline_edit_cancel\n'
            'plone.contentmenu.factories\n'
            'set-portlet-blacklist-status\n'
            'kss_formlib_inline_validation\n'
            'plone_lock_operations\n'
            'calendar_day.html\n'
            'archetypes-querywidget-emptywidget\n'
            'plone.contentmenu.workflow\n'
            'ploneform-macros\n'
            'kss_z3cform_inline_validation\n'
            'sunburstview\n'
            'p.a.jqt.testForm\n'
            'refbrowser_popup\n'
            'kss_javascript\n'
            'replaceField\n'
            'replaceContentRegion\n'
            'kss_formlib_inline_edit_save\n'
            'tinymce-jsonimagesearch\n'
            'etc\n'
            'customizezpt\n'
            'plone.outputfilters_captioned_image\n'
            'saveField\n'
            'tinymce-jsonlinkablefolderlisting\n'
            'foldercontents_update_table\n'
            'refbrowserhelper\n'
            'querybuildernumberofresults\n'
            'base-subpageform.html\n'
            'wickedaddmenu\n'
            'querybuilder_html_results\n'
            'plone_portal_state\n'
            'contentmenurefresh\n'
            'refreshCalendar\n'
            'folder_factories\n'
            'archetypes-querywidget-daterangewidget\n'
            'tinymce-jsonimagefolderlisting\n'
            'updateSharingInfo\n'
            'updateLockInfo\n'
            'checkDocument\n'
            'manage-portlets-macros\n'
            'inlineMovePortletDown\n'
            'togglePortletVisibility\n'
            'five_template\n'
            'calendar_box_view\n'
            'plone_lock_info\n'
            'wickedadd\n'
            'get_macros\n'
            'pas_info\n'
            'candiff\n'
            'replaceWithView\n'
            'plone_interface_info\n'
            'breadcrumbs_view\n'
            'archetypes-querywidget-datewidget\n'
            'search\n'
            'content_anchors\n'
            'inlineMovePortletUp\n'
            'passwordreset_view\n'
            'kssValidateForm\n'
            'full_review_list\n'
            'absolute_url\n'
            'adapter\n'
            'customizezpt.html\n'
            'archetypes-querywidget-referencewidget\n'
            'conversation\n'
            'plone\n'
            'archetypes-querywidget-removecriterialink\n'
            'redirect-to-uuid\n'
            'view_get_menu\n'
            'history\n'
            'copyObject\n'
            'kss_formlib_inline_edit_begin'
        )

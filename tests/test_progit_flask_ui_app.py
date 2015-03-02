# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import unittest
import shutil
import sys
import os

import json
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskApptests(tests.Modeltests):
    """ Tests for flask app of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskApptests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.repo.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    def test_index(self):
        """ Test the index endpoint. """

        output = self.app.get('/')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<h2>All Projects (0)</h2>' in output.data)

        tests.create_projects(self.session)

        output = self.app.get('/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<h2>All Projects (2)</h2>' in output.data)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/?repopage=abc&forkpage=def')
            self.assertTrue(
                '<section class="project_list" id="repos">' in output.data)
            self.assertTrue('<h3>My Forks (0)</h3>' in output.data)
            self.assertTrue(
                '<section class="project_list" id="myforks">' in output.data)
            self.assertTrue('<h3>My Projects (0)</h3>' in output.data)
            self.assertTrue(
                '<section class="project_list" id="myrepos">' in output.data)
            self.assertTrue('<h3>All Projects (2)</h3>' in output.data)

    def test_view_users(self):
        """ Test the view_users endpoint. """

        output = self.app.get('/users/?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>2 users registered.</p>' in output.data)
        self.assertTrue('<a href="/user/pingou">' in output.data)
        self.assertTrue('<a href="/user/foo">' in output.data)

    def test_view_user(self):
        """ Test the view_user endpoint. """

        output = self.app.get('/user/pingou?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<section class="project_list" id="repos">' in output.data)
        self.assertTrue('<h2>Projects (0)</h2>' in output.data)
        self.assertTrue(
            '<section class="project_list" id="forks">' in output.data)
        self.assertTrue('<h2>Forks (0)</h2>' in output.data)

        tests.create_projects(self.session)
        self.gitrepos = tests.create_projects_git(
            progit.APP.config['GIT_FOLDER'])

        output = self.app.get('/user/pingou?repopage=abc&forkpage=def')
        self.assertEqual(output.status_code, 200)
        self.assertTrue(
            '<section class="project_list" id="repos">' in output.data)
        self.assertTrue('<h2>Projects (2)</h2>' in output.data)
        self.assertTrue(
            '<section class="project_list" id="forks">' in output.data)
        self.assertTrue('<h2>Forks (0)</h2>' in output.data)

    def test_new_project(self):
        """ Test the new_project endpoint. """
        # Before
        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 0)
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'tickets', 'project#1.git')))
        self.assertFalse(os.path.exists(
            os.path.join(tests.HERE, 'docs', 'project#1.git')))

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/new/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'Project #1',
            }

            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)
            self.assertTrue(
                '<td class="errors">This field is required.</td>'
                in output.data)

            data['name'] = 'project#1'
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)
            self.assertFalse(
                '<td class="errors">This field is required.</td>'
                in output.data)

            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>New project</h2>' in output.data)
            self.assertTrue(
                '<li class="error">No user &#34;username&#34; found</li>'
                in output.data)

        user.username = 'foo'
        with tests.user_set(progit.APP, user):
            data['csrf_token'] =  csrf_token
            output = self.app.post('/new/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<p>Project #1</p>' in output.data)
            self.assertTrue(
                '<li class="message">Project &#34;project#1&#34; created</li>'
                in output.data)

        # After
        projects = progit.lib.search_projects(self.session)
        self.assertEqual(len(projects), 1)
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'project#1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'tickets', 'project#1.git')))
        self.assertTrue(os.path.exists(
            os.path.join(tests.HERE, 'docs', 'project#1.git')))

    def test_user_settings(self):
        """ Test the user_settings endpoint. """
        self.test_new_project()

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 404)
            self.assertTrue('<h2>Page not found (404)</h2>' in output.data)

        user.username = 'foo'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/settings/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<h2>foo's settings</h2>" in output.data)
            self.assertTrue(
                '<textarea id="ssh_key" name="ssh_key"></textarea>'
                in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'ssh_key': 'this is my ssh key',
            }

            output = self.app.post('/settings/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue("<h2>foo's settings</h2>" in output.data)
            self.assertTrue(
                '<textarea id="ssh_key" name="ssh_key">this is my ssh key'
                '</textarea>' in output.data)

            data['csrf_token'] =  csrf_token

            output = self.app.post(
                '/settings/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Public ssh key updated</li>'
                in output.data)
            self.assertTrue(
                '<section class="project_list" id="repos">' in output.data)
            self.assertTrue(
                '<section class="project_list" id="forks">' in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskApptests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)

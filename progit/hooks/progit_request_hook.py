# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os
import shutil

import flask
import sqlalchemy as sa
import pygit2
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from progit.hooks import BaseHook
from progit.lib.model import BASE, Project
from progit import SESSION, APP


class ProgitRequestsTable(BASE):
    """ Stores information about the progit requests hook deployed on a
    project.

    Table -- hook_progit_requests
    """

    __tablename__ = 'hook_progit_requests'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'progit_hook_requests', cascade="delete, delete-orphan",
            single_parent=True)
        )


class ProgitRequestsForm(wtf.Form):
    ''' Form to configure the progit hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class ProgitRequestHook(BaseHook):
    ''' Progit request hook. '''

    name = 'progit requests'
    form = ProgitRequestsForm
    db_object = ProgitRequestsTable
    backref = 'progit_hook_requests'
    form_fields = ['active']

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')

        # Make sure the hooks folder exists
        hookfolder = os.path.join(repopath, 'hooks')
        if not os.path.exists(hookfolder):
            os.makedirs(hookfolder)

        # Install the main post-receive file
        postreceive = os.path.join(hookfolder, 'post-receive')
        if not os.path.exists(postreceive):
            shutil.copyfile(
                os.path.join(hook_files, 'post-receive'),
                postreceive)
            os.chmod(postreceive, 0755)

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        repo_obj = pygit2.Repository(repopath)

        # Install the hook itself
        shutil.copyfile(
            os.path.join(hook_files, 'progit_hook_requets.py'),
            os.path.join(repopath, 'hooks', 'post-receive.progit')
        )
        os.chmod(
            os.path.join(repopath, 'hooks', 'post-receive.progit'),
            0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_path = os.path.join(
            repopath, 'hooks', 'post-receive.progit')
        if os.path.exists(hook_path):
            os.unlink(hook_path)

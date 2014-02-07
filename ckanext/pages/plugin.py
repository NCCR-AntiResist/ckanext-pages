import logging
from pylons import config

import ckan.plugins as p
import ckan.lib.helpers as h

import actions
import auth
import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

def build_pages_nav_main(*args):

    about_menu = p.toolkit.asbool(config.get('ckanext.pages.about_menu', True))
    group_menu = p.toolkit.asbool(config.get('ckanext.pages.group_menu', True))
    org_menu = p.toolkit.asbool(config.get('ckanext.pages.organization_menu', True))

    new_args = []
    for arg in args:
        if arg[0] == 'about' and not about_menu:
            continue
        if arg[0] == 'organizations_index' and not org_menu:
            continue
        if arg[0] == 'group_index' and not group_menu:
            continue
        new_args.append(arg)

    output = h.build_nav_main(*new_args)

    # do not display any private datasets in menu even for sysadmins
    pages_list = p.toolkit.get_action('ckanext_pages_list')(None, {'order': True, 'private': False})

    page_name = ''

    if (p.toolkit.c.action in ('pages_show', 'blog_show')
       and p.toolkit.c.controller == 'ckanext.pages.controller:PagesController'):
        page_name = p.toolkit.c.environ['routes.url'].current().split('/')[-1]

    for page in pages_list:
        if page['page_type'] == 'blog':
            link = h.link_to(page.get('title'),
                             h.url_for('/blog/' + str(page['name'])))
        else:
            link = h.link_to(page.get('title'),
                             h.url_for('/pages/' + str(page['name'])))

        if page['name'] == page_name:
            li = h.literal('<li class="active">') + link + h.literal('</li>')
        else:
            li = h.literal('<li>') + link + h.literal('</li>')
        output = output + li

    return output

def get_recent_blog_posts(number=5, exclude=None):
    blog_list = p.toolkit.get_action('ckanext_pages_list')(
        None, {'order_publish_date': True, 'private': False,
               'page_type': 'blog'}
    )

    new_list = []
    for blog in blog_list:
        if exclude and blog['name'] == exclude:
            continue
        new_list.append(blog)
        if len(new_list) == number:
            break
        try:
            parsed_xml = ET.fromstring(blog['content'])
        except ET.ParseError:
            continue

        image_tag = parsed_xml.find('img')
        if image_tag is not None:
            image = image_tag.attrib['src']
            blog['image'] = image

    return new_list



class PagesPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions, inherit=True)
    p.implements(p.IAuthFunctions, inherit=True)

    def update_config(self, config):
        self.organization_pages = p.toolkit.asbool(config.get('ckanext.pages.organization', False))
        self.group_pages = p.toolkit.asbool(config.get('ckanext.pages.group', False))

        p.toolkit.add_template_directory(config, 'theme/templates_main')
        if self.group_pages:
            p.toolkit.add_template_directory(config, 'theme/templates_group')
        if self.organization_pages:
            p.toolkit.add_template_directory(config, 'theme/templates_organization')

        p.toolkit.add_resource('theme/public', 'ckanext-pages')
        p.toolkit.add_public_directory(config, 'theme/public')

    def configure(self, config):
        return

    def get_helpers(self):
        return {
            'build_nav_main': build_pages_nav_main,
            'get_recent_blog_posts': get_recent_blog_posts
        }

    def after_map(self, map):
        controller = 'ckanext.pages.controller:PagesController'

        if self.organization_pages:
            map.connect('organization_pages_delete', '/organization/pages_delete/{id}{page:/.*|}',
                        action='org_delete', ckan_icon='delete', controller=controller)
            map.connect('organization_pages_edit', '/organization/pages_edit/{id}{page:/.*|}',
                        action='org_edit', ckan_icon='edit', controller=controller)
            map.connect('organization_pages', '/organization/pages/{id}{page:/.*|}',
                        action='org_show', ckan_icon='file', controller=controller, highlight_actions='org_edit org_show')

        if self.group_pages:
            map.connect('group_pages_delete', '/group/pages_delete/{id}{page:/.*|}',
                        action='group_delete', ckan_icon='delete', controller=controller)
            map.connect('group_pages_edit', '/group/pages_edit/{id}{page:/.*|}',
                        action='group_edit', ckan_icon='edit', controller=controller)
            map.connect('group_pages', '/group/pages/{id}{page:/.*|}',
                        action='group_show', ckan_icon='file', controller=controller, highlight_actions='group_edit group_show')


        map.connect('pages_delete', '/pages_delete{page:/.*|}',
                    action='pages_delete', ckan_icon='delete', controller=controller)
        map.connect('pages_edit', '/pages_edit{page:/.*|}',
                    action='pages_edit', ckan_icon='edit', controller=controller)
        map.connect('pages_show', '/pages{page:/.*|}',
                    action='pages_show', ckan_icon='file', controller=controller, highlight_actions='pages_edit pages_show')
        map.connect('pages_upload', '/pages_upload',
                    action='pages_upload', controller=controller)

        map.connect('blog_delete', '/blog_delete{page:/.*|}',
                    action='blog_delete', ckan_icon='delete', controller=controller)
        map.connect('blog_edit', '/blog_edit{page:/.*|}',
                    action='blog_edit', ckan_icon='edit', controller=controller)
        map.connect('blog_show', '/blog{page:/.*|}',
                    action='blog_show', ckan_icon='file', controller=controller, highlight_actions='blog_edit blog_show')
        return map

    def get_actions(self):
        actions_dict = {
            'ckanext_pages_show': actions.pages_show,
            'ckanext_pages_update': actions.pages_update,
            'ckanext_pages_delete': actions.pages_delete,
            'ckanext_pages_list': actions.pages_list,
            'ckanext_pages_upload': actions.pages_upload,
        }
        if self.organization_pages:
            org_actions={
                'ckanext_org_pages_show': actions.org_pages_show,
                'ckanext_org_pages_update': actions.org_pages_update,
                'ckanext_org_pages_delete': actions.org_pages_delete,
                'ckanext_org_pages_list': actions.org_pages_list,
            }
            actions_dict.update(org_actions)
        if self.group_pages:
            group_actions={
                'ckanext_group_pages_show': actions.group_pages_show,
                'ckanext_group_pages_update': actions.group_pages_update,
                'ckanext_group_pages_delete': actions.group_pages_delete,
                'ckanext_group_pages_list': actions.group_pages_list,
            }
            actions_dict.update(group_actions)
        return actions_dict

    def get_auth_functions(self):
        return {
            'ckanext_pages_show': auth.pages_show,
            'ckanext_pages_update': auth.pages_update,
            'ckanext_pages_delete': auth.pages_delete,
            'ckanext_pages_list': auth.pages_list,
            'ckanext_pages_upload': auth.pages_upload,
            'ckanext_org_pages_show': auth.org_pages_show,
            'ckanext_org_pages_update': auth.org_pages_update,
            'ckanext_org_pages_delete': auth.org_pages_delete,
            'ckanext_org_pages_list': auth.org_pages_list,
            'ckanext_group_pages_show': auth.group_pages_show,
            'ckanext_group_pages_update': auth.group_pages_update,
            'ckanext_group_pages_delete': auth.group_pages_delete,
            'ckanext_group_pages_list': auth.group_pages_list,
       }

try:
    from bson import ObjectId
except ImportError:  # old pymongo
    from pymongo.objectid import ObjectId

from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse

from gnowsys_ndf.ndf.models import Node, GSystem, GSystemType, RelationType, Group
from gnowsys_ndf.ndf.models import node_collection, triple_collection
from gnowsys_ndf.ndf.views.methods import get_group_name_id, get_language_tuple, create_grelation
from gnowsys_ndf.settings import GSTUDIO_DEFAULT_LANGUAGE

# gst_page_name, gst_page_id = GSystemType.get_gst_name_id(u'Page')
rt_translation_of = Node.get_name_id_from_type('translation_of', 'RelationType', get_obj=True)
supported_languages = ['Hindi', 'Telugu']


def all_translations(request, group_id, node_id):
    '''
    returns all translated nodes of provided node.
    '''
    node_obj = Node.get_node_by_id(node_id)
    # node_translation_grels = node_obj.get_relation('translation_of', status='PUBLISHED')
    # return node_translation_grels

    # node_translation_grels = node_obj.get_relation('translation_of')
    all_translation_nodes = node_obj.get_relation_right_subject_nodes('translation_of')

    return render_to_response("ndf/translation_list.html",
                              {
                                'group_id': Group.get_group_name_id(group_id)[1],
                                'groupid': Group.get_group_name_id(group_id)[1],
                                'nodes': all_translation_nodes,
                                'node': node_obj,
                                'source_node_id': node_id,
                                'card_url_name': 'show_translation',
                                'supported_languages': supported_languages
                               },
                              context_instance=RequestContext(request))


def show_translation(request, group_id, node_id, lang):
    '''
    for VIEW/READ: show translated provided node to provided LANG CODE
    lang could be either proper/full language-name/language-code
    '''
    node = translated_node_id = None
    grel_node = triple_collection.one({
                            '_type': 'GRelation',
                            'subject': ObjectId(node_id),
                            'relation_type': rt_translation_of._id,
                            'language': get_language_tuple(lang),
                            # 'status': 'PUBLISHED'
                        })

    if grel_node:
        node = Node.get_node_by_id(grel_node.right_subject)
        translated_node_id = node._id

    # code to show other translations
    other_translations_grels = triple_collection.find({
                            '_type': u'GRelation',
                            'subject': ObjectId(node_id),
                            'relation_type': rt_translation_of._id,
                            'right_subject': {'$nin': [translated_node_id]}
                        })

    other_translations = node_collection.find({'_id': {'$in': [r.right_subject for r in other_translations_grels]} })

    # --- END of code to show other translations

    return render_to_response("ndf/translate_detail.html",
                          {
                            'group_id': Group.get_group_name_id(group_id)[1],
                            'groupid': Group.get_group_name_id(group_id)[1],
                            'source_node_id': node_id,
                            'source_node_obj': Node.get_node_by_id(node_id),
                            'node': node,
                            'other_translations': other_translations,
                            'card_url_name': 'show_translation',
                           },
                          context_instance=RequestContext(request))



@login_required
def translate(request, group_id, node_id, lang, translated_node_id=None, **kwargs):
    '''
    for EDIT: translate provided node to provided LANG CODE
    lang could be either proper/full language-name/language-code
    `node_id` is _id of source node.
    '''
    group_name, group_id = Group.get_group_name_id(group_id)
    language = get_language_tuple(lang)
    source_obj = Node.get_node_by_id(node_id)

    existing_grel = translate_grel = translated_node = None

    if translated_node_id:
        translated_node = Node.get_node_by_id(translated_node_id)
    else:
        # get translated_node
        existing_grel = triple_collection.one({
                                            '_type': 'GRelation',
                                            'subject': ObjectId(node_id),
                                            'relation_type': rt_translation_of._id,
                                            'language': language
                                        })

        if existing_grel:
            # get existing translated_node
            translated_node = Node.get_node_by_id(existing_grel.right_subject)
            translate_grel = existing_grel

    if request.method == 'GET':
        return render_to_response("ndf/translate_form.html",
                              {
                                'group_id': group_id,
                                'node_obj': translated_node,
                                'source_obj': source_obj,
                                'url': reverse('translate', kwargs={
                                        'group_id': group_id,
                                        'node_id': node_id,
                                        'lang': lang,
                                        })
                               },
                              context_instance=RequestContext(request))

    elif request.method == 'POST':  # explicit `if` check for `POST`
        if not translated_node:
            # create a new translated new
            # translated_node = node_collection.collection.GSystem()
            # copy source_obj's data into a new
            translated_node = source_obj.__deepcopy__()
            translated_node['_id'] = ObjectId()

        translated_node.fill_gstystem_values(request=request,
                                            language=language,
                                            **kwargs)
        translated_node.save(group_id=group_id)
        if not existing_grel:
            translate_grel = create_grelation(node_id, rt_translation_of, translated_node._id, language=language)

    # page_gst_name, page_gst_id = Node.get_name_id_from_type('Page', 'GSystemType')
    # return HttpResponseRedirect(reverse('page_details', kwargs={'group_id': group_id, 'app_id': page_gst_id }))
    # return HttpResponseRedirect(reverse('all_translations', kwargs={'group_id': group_id, 'node_id': node_id }))
    return HttpResponseRedirect(reverse('show_translation', kwargs={'group_id': group_id, 'node_id': node_id, 'lang': lang }))
    # return translated_node, translate_grel
from flask import Flask, send_from_directory, request, jsonify, Response
from oio.api.object_storage import ObjectStorageAPI
import optparse
import mimetypes
from elasticsearch import Elasticsearch
from flask import abort



def parse():
    parser = optparse.OptionParser()
    parser.add_option("-n", "--namespace", help="Namespace to use")
    parser.add_option("-u", "--url", help="OIO-Proxy IP:PORT")
    parser.add_option("-a", "--account", help="Account to use")
    parser.add_option("-p", "--port", help="OpenIO browser ports")
    parser.add_option("-e", "--elasticsearch", help="elasticsearch IP")
    options, _ = parser.parse_args()
    return options

def get_extensions_for_type(general_type):
    for ext in mimetypes.types_map:
        if mimetypes.types_map[ext].split('/')[0] == general_type:
            yield ext


def init_sds_osapi(ns, url):
    try:
        return ObjectStorageAPI(ns, url)
    except Exception as e:
        raise Exception('Could not access API at %s' % url)

options = parse()

PROXY_URL = options.url
ELASTICSEARCH = options.elasticsearch or "127.0.0.1"
BROWSER_PORT = int(options.port) or 8000
if not options.url:
    raise ValueError('Please set oioproxy url using --url parameter')
NAMESPACE = options.namespace or 'OPENIO'
ACCOUNT = options.account or 'default'
API = init_sds_osapi(NAMESPACE, PROXY_URL)

# Create some containers for now
#API.container_create(ACCOUNT, "Documents")
#API.container_create(ACCOUNT, "Cat Videos")
#API.container_create(ACCOUNT, "Work")
API.container_create(ACCOUNT, "img")
API.container_create(ACCOUNT, "static")
#API.object_create(ACCOUNT, "static", file_or_path="./no_image.png")
#API.object_create(ACCOUNT, "static", file_or_path="./openio.png")

app = Flask(__name__, static_url_path='')
#app.debug = True
if app.debug is not True:
    import logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler('python.log', maxBytes=1024 * 1024 * 100, backupCount=20)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)


@app.route('/')
def index_alias():
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/api/containers/<cont>/objects', methods=['POST'])
def upload_object(cont):
    if 'file' not in request.files:
        return "400"
    f = request.files['file']
    if f.filename == '':
        return "400"
    API.object_create(ACCOUNT, cont.strip(), file_or_path=f,
                      obj_name=f.filename.strip())
    return "200"


@app.route('/api/containers/<cont>/objects/<obj>/download')
def download_object(cont, obj):
    meta, stream = API.object_fetch(ACCOUNT, cont, obj=obj)
    headers = {
        "Content-Disposition": "attachment; filename=%s" % meta['name']
    }
    return Response(stream, direct_passthrough=True,
                    mimetype=meta['mime_type'], headers=headers)

@app.route('/api/containers/<cont>/objects/<obj>/preview')
def preview_object(cont, obj):
    #print cont
    try:
        meta, stream = API.object_fetch(ACCOUNT, cont, obj=obj)
        ext = obj.split(".")
        ext = '.' + ext[len(ext)-1].lower()
        mimetypes.init()
        img_type = tuple(get_extensions_for_type('image'))
        video_type = tuple(get_extensions_for_type('video'))
        if ext in img_type:
            headers = {
                "Content-Disposition": "filename=%s" % meta['name'],
                "Cache-Control": 'public, max-age=3600'
            }
            return Response(stream, direct_passthrough=True,
                    mimetype=mimetypes.types_map[ext], headers=headers)
        elif ext in video_type:
            headers = {
                "Content-Disposition": "inline; filename=%s" % meta['name'],
                "Cache-Control": 'public, max-age=3600'
            }
            return Response(stream, direct_passthrough=True,
                    mimetype=mimetypes.types_map[ext], headers=headers)
        else:
            #meta, stream = API.object_fetch(ACCOUNT, "static", obj="no_image.png")
            #ext = ".png"
            headers = {
                "Content-Disposition": "filename=%s" % meta['name'],
                "Cache-Control": 'public, max-age=3600'
            }
            return Response(stream, direct_passthrough=True,
                    mimetype=mimetypes.types_map[ext], headers=headers)
    except Exception as e:
        meta, stream = API.object_fetch(ACCOUNT, "static", obj="no_image.png")
        ext = ".png"
        headers = {
                "Content-Disposition": "filename=%s" % meta['name'],
                "Cache-Control": 'public, max-age=3600'
            }
        return Response(stream, direct_passthrough=True,
                    mimetype=mimetypes.types_map[ext], headers=headers)


@app.route('/api/containers/<cont>/objects/search/<prefix>', methods=['GET'])
def search_objects(cont, prefix):
    es = Elasticsearch([ELASTICSEARCH])
    query = []
    for pref in prefix.split(" "):
        pref = pref.lower()
        if pref:
            regexp = {
                'regexp': { 'properties.autocategory': '.*%s.*'%pref }
                }
            query.append(regexp)
            regexp = {
                'regexp': { 'name': '.*%s.*'%pref }
                }
            query.append(regexp)
    res = es.search(index=ACCOUNT.lower(), doc_type=cont.lower(), body={"from" : 0, "size" : 100, "query": { "bool": { "should": query } }})
    #print res
    res_search = {}
    objects = []
    img_type = tuple(get_extensions_for_type('image'))
    for hit in res["hits"]["hits"]:
        ext = hit['_source']['name'].split(".")
        ext = '.' + ext[len(ext)-1].lower()
        if ext in img_type:
            imaget = True
        else:
            imaget = False
        object = {
            'hash': hit['_source']['hash'],
            'mime_type': hit['_source']['mime_type'],
            'name': hit['_source']['name'],
            'properties': hit['_source']['properties'],
            'size': hit['_source']['length'],
            'image': imaget
            }
        objects.append(object)

    properties = {
        'sys.account': ACCOUNT,
        'sys.ns': NAMESPACE,
        'sys.user.name': cont
        }

    res_search = {
        'objects': objects,
        'properties': properties
        }
    return jsonify(**res_search)

@app.route('/api/containers/<cont>/objects/<marker>', methods=['GET'])
@app.route('/api/containers/<cont>/objects/', methods=['GET'])
@app.route('/api/containers/<cont>/objects', methods=['GET'])
def list_objects(cont, marker=None, prefix=None):
    mimetypes.init()
    img_type = tuple(get_extensions_for_type('image'))
    video_type = tuple(get_extensions_for_type('video'))
    try:
        res = API.object_list(ACCOUNT, cont, limit=10000, marker=marker,
                              prefix=prefix, properties=True)
    except Exception as e:
        return abort(404)
    #res2 = {}
    i = 0
    for obj in res['objects']:
        ext = obj['name'].split(".")
        ext = '.' + ext[len(ext)-1].lower()
        #print ext
        if ext in img_type:
            res['objects'][i]['image'] = True
        elif ext in video_type:
            res['objects'][i]['video'] = True
            res['objects'][i]['mime_type'] = mimetypes.types_map[ext]
        elif ext == ".mkv":
            res['objects'][i]['other'] = True
        else:
            res['objects'][i]['other'] = True
            try:
                mtype = mimetypes.types_map[ext]
            except Exception as e:
                #print e
                pass
            else:
                res['objects'][i]['mime_type'] = mimetypes.types_map[ext]
        #res2 += obj
        i += 1
    #print res

    return jsonify(**res)

@app.route('/api/containers/<cont>/create')
def create_container(cont):
    res = API.container_create(ACCOUNT, cont)
    return "200"

@app.route('/api/containers/<marker>', methods=['GET'])
@app.route('/api/containers/', methods=['GET'])
@app.route('/api/containers', methods=['GET'])
def list_containers(marker=None):
    try:
        res = API.container_list(ACCOUNT, limit=200, marker=marker)
    except:
        return abort(404)
    #print res
    return jsonify({'containers': res})


if __name__ == "__main__":
    #app.run(host='0.0.0.0',port=BROWSER_PORT,threaded=True)
    app.run(host='0.0.0.0',port=BROWSER_PORT)
    API.object_create(ACCOUNT, "static", file_or_path="./no_image.png")

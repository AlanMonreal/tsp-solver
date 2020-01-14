from urllib.request import HTTPError
from json import JSONDecodeError
from arcgis import ArcgisError
#import traceback
import sys

internalError = {'error':'internalError', 'errorMsg':'Internal error'}

def handleError():
    """ Call this function from inside except clause """
    try:
        raise
    except HTTPError as err:
        print('Connection failed with HTTP code {}: {}\n on url: {}'.format(str(err.code), str(err.reason), err.url))
        return internalError
    except JSONDecodeError as err:
        print('Error decoding json:',err.msg)
        return internalError
    except ArcgisError as err:
        print('Error in arcgis subsystem "{}": {}'.format(err.system, err.message))
        return internalError
    # TODO: Add key error exception
    except Exception as err:
        print('Unhandled exception:', type(err).__name__)
        print('Description:', err)
        print('In file:', sys.exc_info()[-1].tb_frame.f_code.co_filename)
        print('In line:', sys.exc_info()[-1].tb_lineno)
        #print(traceback.format_exc())
        return internalError

def logError(msg):
    # Not implemented
    pass

'''
TODO:
* return json with "error" key
* log traceback
'''

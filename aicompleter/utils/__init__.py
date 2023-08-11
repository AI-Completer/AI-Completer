'''
Utils for aicompleter
'''
from .endict import (
    defaultdict,
    EnhancedDict,
    DataModel,
)
from .aio import (
    ainput,
    aprint,
    thread_run,
    is_enable,
)
from .etype import (
    Struct,
    StructType,
    typecheck,
    hookclass,
    appliable_parameters,
    make_model,
    TaskList,
    stack_varibles,
    link_property,
)
from .launch import (
    launch,
    start,
    run_handler,
)
from .typeval import (
    is_generic,
    is_base_generic,
    is_qualified_generic,
    get_base_generic,
    get_subtypes,
    is_instance,
    is_subtype,
    python_type,
    verify,
    get_signature,
    makeoverload,
    makeoverloadmethod,
)
from .text import (
    RemoteWebPage,
    getChunkedText,
    getChunkedToken,
    getChunkedWebText,
    getWebText,
    download,
    extract_text,
    extract_html,
    clear_html,
)
from .stroage import (
    Stroage,
    StroageManager,
)
    
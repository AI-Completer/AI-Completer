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
    aiterfunc,
    retry,
    retry_async,
)
from .etype import (
    Struct,
    StructType,
    typecheck,
    hookclass,
    appliable_parameters,
    BaseModel,
    make_model,
    asdict,
    TaskList,
    stack_varibles,
    link_property,
    getframe,
    getcaller,
    getcallerclass,
    getcallerclassinstance,
    require_module,
    get_inherit_methods,
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
from .storage import (
    Storage,
    StorageManager,
)

import ast
from enum import Enum

from pydantic import BaseModel


class ChunkType(str, Enum):
    FUNCTION = "function"
    ASYNC_FUNCTION = "async_function"
    METHOD = "method"
    CLASS = "class"
    MODULE_LEVEL = "module_level"
    CLASS_HEADER = "class_header"


class CodeChunk(BaseModel):
    content: str
    file_path: str
    start_line: int
    end_line: int
    node_type: ChunkType
    name: str
    parent_class: str | None = None
    is_generated: bool

def get_effective_start_lineno(node):
    if node.decorator_list:
        return node.decorator_list[0].lineno
    else:
        return node.lineno

def is_overload_function(node):
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id =="overload" or isinstance(decorator,ast.Attribute) and decorator.attr =="overload":
            return True

    return False





def build_chunk(node, node_type, source, file_path, is_generated, parent_class=None,end_line=None):
    start_line = get_effective_start_lineno(node)
    if end_line is None:
        end_line=node.end_lineno
    lines = source.splitlines()
    content = lines[start_line-1:end_line]
    content = "\n".join(content)
    return CodeChunk(
        content=content,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        node_type=node_type,
        name=node.name,
        parent_class=parent_class,
        is_generated=is_generated )

class ChunkVisitor(ast.NodeVisitor):
    def __init__(self,source,file_path,is_generated):
        self.source = source
        self.file_path = file_path
        self.is_generated = is_generated
        self.current_class = None
        self.chunks =[]


    def visit_FunctionDef(self, node):
        if(is_overload_function(node)):
            return
        node_type = ChunkType.METHOD if self.current_class else ChunkType.FUNCTION
        chunk = build_chunk(
            node=node,node_type=node_type,source=self.source,file_path=self.file_path,
            is_generated=self.is_generated, parent_class=self.current_class)
        self.chunks.append(chunk)


    def visit_AsyncFunctionDef(self, node):
        if(is_overload_function(node)):
            return
        node_type = ChunkType.METHOD if self.current_class else ChunkType.ASYNC_FUNCTION
        chunk = build_chunk(node,node_type,self.source, self.file_path, 
                            self.is_generated, self.current_class)
        self.chunks.append(chunk)

    def visit_ClassDef(self, node):
        method_count = sum(isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                           for child in node.body)

        if method_count >=2:
            if node.decorator_list:
                node_type = ChunkType.CLASS_HEADER
                end_line = node.lineno

                chunk = build_chunk(node=node, node_type=node_type,source=self.source, file_path=self.file_path,
                                    is_generated=self.is_generated,end_line=end_line)

                self.chunks.append(chunk)

            self.current_class = node.name
            for child in node.body:
                self.visit(child)

            self.current_class = None

        else:
           chunk = build_chunk(node= node,node_type=ChunkType.CLASS, source=self.source,
                               file_path=self.file_path, is_generated=self.is_generated, parent_class=None)
           self.chunks.append(chunk)


    def visit_Module(self, node):
        module_nodes = []
        lines = self.source.splitlines()

        def flush_module_nodes():
            if not module_nodes:
                return

            content = lines[module_nodes[0].lineno -1 : module_nodes[-1].end_lineno]
            content = "\n".join(content)
        
        
            chunk = CodeChunk(
                    content=content,
                    file_path=self.file_path,
                    start_line=module_nodes[0].lineno,
                    end_line=module_nodes[-1].end_lineno,
                    node_type=ChunkType.MODULE_LEVEL,
                    name="<module>",
                    parent_class=None,
                    is_generated=self.is_generated
                )
        
            self.chunks.append(chunk)
            module_nodes.clear()

            
        

        for child in node.body:
            if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                module_nodes.append(child)
            else:
                flush_module_nodes()
                self.visit(child)

        flush_module_nodes()


def chunk_file(source,filepath,is_generated):
    tree = ast.parse(source)\

    filepath = filepath.replace("\\", "/")

    visitor = ChunkVisitor(source,filepath,is_generated)

    visitor.visit(tree)

    return visitor.chunks

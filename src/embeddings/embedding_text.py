from src.chunker.chunking import CodeChunk


def build_embedding_text(chunk: CodeChunk) -> str:
    lines = [f"File: {chunk.file_path}",
             f"Symbol: {chunk.name}",
             f"Type: {chunk.node_type.value}"]

    if chunk.parent_class:
        lines.append(f"Parent Class: {chunk.parent_class}")

    lines.append(f"Content: {chunk.content}")

    return "\n".join(lines)

   

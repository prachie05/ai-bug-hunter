def retrieve(query,k,backend,store):
    

    query_embedding = backend.embed([query])[0]

    result = store.search(query_embedding,k)

    code_chunks = []
    for chunk, score in result:
            code_chunks.append(chunk)

    return code_chunks


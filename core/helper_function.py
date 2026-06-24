# def get_branch_id(request):
#     return request.auth.get("branch") if request.auth else None

def get_branch_id(request):
    print("AUTH PAYLOAD:", request.auth)
    print(
        "TOKEN ORG:",
        request.auth.get("organization_id")
        if request.auth else None
    )

    print(
        "TOKEN BRANCH:",
        request.auth.get("branch_id")
        if request.auth else None
    )
    return request.auth.get("branch_id") if request.auth else None

def get_organization_id(request):
    return request.auth.get("organization_id") if request.auth else None

from __future__ import annotations

from fastapi.testclient import TestClient


def test_prompt_template_crud(runtime_app) -> None:
    client = TestClient(runtime_app)

    create_response = client.post(
        '/api/prompt-templates',
        json={
            'kind': 'script',
            'name': '脚本改写模板',
            'description': '用于脚本段落改写',
            'content': '请基于当前段落和要求输出新版本。',
        },
    )

    assert create_response.status_code == 200
    created = create_response.json()['data']
    assert created['kind'] == 'script'
    template_id = created['id']

    list_response = client.get('/api/prompt-templates', params={'kind': 'script'})
    assert list_response.status_code == 200
    listed = list_response.json()['data']
    assert len(listed) == 1
    assert listed[0]['id'] == template_id

    update_response = client.put(
        f'/api/prompt-templates/{template_id}',
        json={
            'kind': 'script',
            'name': '脚本改写模板-更新',
            'description': '更新后的模板说明',
            'content': '只输出修改后的完整脚本。',
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()['data']
    assert updated['name'] == '脚本改写模板-更新'

    delete_response = client.delete(f'/api/prompt-templates/{template_id}')
    assert delete_response.status_code == 200
    assert delete_response.json()['data']['deleted'] is True

    empty_response = client.get('/api/prompt-templates')
    assert empty_response.status_code == 200
    assert empty_response.json()['data'] == []

"""
Metadata addon default settings
"""
MAPPINGS = [
    {
        'schema': '公的資金による研究データのメタデータ登録',
        'items': {
            'grdm-file:title-ja': {
                'type': 'string',
                'jsonpath': 'file.name',
            },
            'grdm-file:title-en': {
                'type': 'string',
                'jsonpath': 'file.name',
            },
            'grdm-file:creators': {
                'type': 'jsonarray',
                'jsonpath': 'node.contributors',
                'template': {
                    'type': 'jsonobject',
                    'jsonpath': '$',
                    'template': {
                        'name_en': {
                            'type': 'string',
                            'jsonpath': '$.given_name + " " + $.family_name',
                        },
                        'name_ja': {
                            'type': 'string',
                            'jsonpath': '$.family_name_ja + $.given_name_ja',
                        },
                    },
                },
            },
            'grdm-file:hosting-inst-ja': {
                'type': 'string',
                'jsonpath': 'node.affiliated_institutions[0].name',
            },
            'grdm-file:hosting-inst-en': {
                'type': 'string',
                'jsonpath': 'node.affiliated_institutions[0].name',
            },
            'grdm-file:data-man-name-ja': {
                'type': 'string',
                'jsonpath': 'node.contributors[?permissions.admin].family_name_ja + node.contributors[?permissions.admin].given_name_ja',
            },
            'grdm-file:data-man-name-en': {
                'type': 'string',
                'jsonpath': 'node.contributors[?permissions.admin].given_name + " " + node.contributors[?permissions.admin].family_name',
            },
        }
    },
    {
        'schema': 'WEKO3 デフォルトアイテムタイプ',
        'items': {
            'grdm-file:Title.ja': {
                'type': 'string',
                'jsonpath': 'file.name',
            },
            'grdm-file:Title.en': {
                'type': 'string',
                'jsonpath': 'file.name',
            },
            'grdm-file:Creator': {
                'type': 'jsonarray',
                'jsonpath': 'node.contributors',
                'template': {
                    'type': 'jsonobject',
                    'jsonpath': '$',
                    'template': {
                        'name_en': {
                            'type': 'string',
                            'jsonpath': '$.given_name + " " + $.family_name',
                        },
                        'name_ja': {
                            'type': 'string',
                            'jsonpath': '$.family_name_ja + $.given_name_ja',
                        },
                    },
                },
            },
            'grdm-file:Contributor': {
                'type': 'jsonarray',
                'jsonpath': 'node.contributors',
                'template': {
                    'type': 'jsonobject',
                    'jsonpath': '$',
                    'template': {
                        'name_en': {
                            'type': 'string',
                            'jsonpath': '$.given_name + " " + $.family_name',
                        },
                        'name_ja': {
                            'type': 'string',
                            'jsonpath': '$.family_name_ja + $.given_name_ja',
                        },
                    },
                },
            },
        }
    },
    {
        'schema': '公的資金による研究データのメタデータ登録',
        'base': 'WEKO3 デフォルトアイテムタイプ',
        'items': {
            'grdm-file:title-ja': {
                'type': 'string',
                'jsonpath': 'base."grdm-file:Title.ja"',
            },
            'grdm-file:title-en': {
                'type': 'string',
                'jsonpath': 'base."grdm-file:Title.en"',
            },
        }
    },
]

import json

with open(r'C:\Users\qlm4e\Downloads\fraud-detection-v2\fraud-detection\ml\models\training_summary.json') as f:
    summary = json.load(f)

results = summary['results']

if 'xgboost' in results:
    xgb = results['xgboost']
    meta = {
        'algorithm': 'xgboost',
        'threshold': xgb['threshold'],
        'precision': xgb['precision'],
        'recall': xgb['recall'],
        'f1': xgb['f1'],
        'auc_roc': xgb['auc_roc'],
        'pr_auc': xgb['pr_auc'],
        'mcc': xgb['mcc'],
        'confusion_matrix': xgb['confusion_matrix'],
        'hyperparams': xgb.get('hyperparams', {}),
    }
    with open(r'C:\Users\qlm4e\Downloads\fraud-detection-v2\fraud-detection\backend\app\ml\artifacts\xgboost_metadata.json', 'w') as f:
        json.dump(meta, f, indent=2)
    print("Created xgboost_metadata.json: threshold=%s pr_auc=%s" % (meta['threshold'], meta['pr_auc']))

if 'logistic_regression' in results:
    lr = results['logistic_regression']
    meta = {
        'algorithm': 'logistic_regression',
        'threshold': lr['threshold'],
        'precision': lr['precision'],
        'recall': lr['recall'],
        'f1': lr['f1'],
        'auc_roc': lr['auc_roc'],
        'pr_auc': lr['pr_auc'],
        'mcc': lr['mcc'],
        'confusion_matrix': lr['confusion_matrix'],
    }
    with open(r'C:\Users\qlm4e\Downloads\fraud-detection-v2\fraud-detection\backend\app\ml\artifacts\lr_metadata.json', 'w') as f:
        json.dump(meta, f, indent=2)
    print("Created lr_metadata.json: threshold=%s pr_auc=%s" % (meta['threshold'], meta['pr_auc']))

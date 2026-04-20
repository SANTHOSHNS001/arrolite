
import os
from datetime import datetime

from django.db import models
from django.utils.text import slugify


import os
from datetime import datetime
from django.utils.text import slugify

import os
from datetime import datetime
from django.utils.text import slugify

def product_image_upload_path(instance, filename):
    """
    Upload path:
    Category/<subcategory_or_category>/<product_id>/<timestamped_filename>
    """
    product = instance.product
    now = datetime.now().strftime('%d%m%y_%H%M')
    ext = os.path.splitext(filename)[1] or '.png'

    # Determine category or subcategory
    if product.subcategory:
        category_part = slugify(product.subcategory.name)
    elif product.category:
        category_part = slugify(product.category.name)
    else:
        category_part = 'uncategorized'

    product_id = product.id or 'new'
    filename = f"{slugify(product.name)}_{now}{ext}"

    return f"Category/{category_part}/{product_id}/{filename}"


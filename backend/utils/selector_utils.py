def get_css_selector(element):
    """Generate a CSS selector for a given element"""
    if element.id:
        return f"#{element.id}"
    
    if element.class_name:
        classes = element.class_name.split()
        if classes:
            return f"{element.tag_name}.{'.'.join(classes)}"
    
    # Try with attributes
    if element.get_attribute("name"):
        return f"{element.tag_name}[name='{element.get_attribute('name')}']"
    
    # Fallback to XPath
    return element.get_xpath()
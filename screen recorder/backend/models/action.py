class Action:
    def __init__(self, action_type, **kwargs):
        self.type = action_type
        self.timestamp = kwargs.get('timestamp')
        self.selector = kwargs.get('selector')
        self.value = kwargs.get('value')
        self.url = kwargs.get('url')
        self.innerText = kwargs.get('innerText')
        self.tagName = kwargs.get('tagName')
        self.inputType = kwargs.get('inputType')
        
    def to_dict(self):
        result = {'type': self.type, 'timestamp': self.timestamp}
        
        if self.selector:
            result['selector'] = self.selector
        if self.value:
            result['value'] = self.value
        if self.url:
            result['url'] = self.url
        if self.innerText:
            result['innerText'] = self.innerText
        if self.tagName:
            result['tagName'] = self.tagName
        if self.inputType:
            result['inputType'] = self.inputType
            
        return result
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            action_type=data.get('type'),
            timestamp=data.get('timestamp'),
            selector=data.get('selector'),
            value=data.get('value'),
            url=data.get('url'),
            innerText=data.get('innerText'),
            tagName=data.get('tagName'),
            inputType=data.get('inputType')
        )
def contextualyzeProjectProperties(context, project) {
	for (propertyName in project.getPropertyNames()) {
		context[propertyName] = project.getPropertyValue(propertyName)
	}
}
# $Id$


REMOTE_HOST=bandsaw.sourceforge.net
REMOTE_DIR=/home/groups/b/ba/bandsaw/htdocs
REMOTE_USER=ashtong


upload: .upload-root .upload-news .upload-ssi .upload-images \
	.upload-screenshots


.upload-root: *.html .htaccess default.css
	scp $? $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)
	@touch .upload-root


.upload-news: news/*.html
	#ssh $(REMOTE_USER)@$(REMOTE_HOST) mkdir -p $(REMOTE_DIR)/news
	scp $? $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/news
	@touch .upload-news


.upload-ssi: ssi/*.html
	#ssh $(REMOTE_USER)@$(REMOTE_HOST) mkdir -p $(REMOTE_DIR)/ssi
	scp $? $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/ssi
	@touch .upload-ssi


.upload-images: images/*.png
	#ssh $(REMOTE_USER)@$(REMOTE_HOST) mkdir -p $(REMOTE_DIR)/images
	scp $? $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/images
	@touch .upload-images


.upload-screenshots: images/ss/*.png images/ss/*.gif
	#ssh $(REMOTE_USER)@$(REMOTE_HOST) mkdir -p $(REMOTE_DIR)/images/ss
	scp $? $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_DIR)/images/ss
	@touch .upload-screenshots

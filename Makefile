ANTLR_VER=3.1.3
ANTLR_DIR=antlr-${ANTLR_VER}
ANTLR_TAR=${ANTLR_DIR}.tar.gz
ANTLR_JAR=${ANTLR_DIR}/lib/antlr-${ANTLR_VER}.jar
ANTLR_PKG=http://www.antlr.org/download/${ANTLR_TAR}

BUILD_DIR=build
GRAMMAR_FILE=Jump.g

.PHONY: all clean test tidy

all: ${BUILD_DIR}/__init__.py

${BUILD_DIR}:
	@mkdir -p ${BUILD_DIR}
	@touch ${BUILD_DIR}

${ANTLR_TAR}:
	wget ${ANTLR_PKG}

${ANTLR_DIR}: ${ANTLR_TAR}
	tar zxf ${ANTLR_DIR}.tar.gz
	@touch ${ANTLR_DIR}

${BUILD_DIR}/__init__.py: ${ANTLR_DIR} ${BUILD_DIR} ${GRAMMAR_FILE}
	java -cp ${ANTLR_JAR} org.antlr.Tool -o ${BUILD_DIR} ${GRAMMAR_FILE}
	@touch ${BUILD_DIR}/__init__.py

test: all
	bash test.sh

tidy:
	rm -r ${BUILD_DIR} *.pyc

clean: tidy
	rm -r ${ANTLR_DIR}

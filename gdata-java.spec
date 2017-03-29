%{?_javapackages_macros:%_javapackages_macros}

%define commit c6202a55f5f29afb37ffcf876674dca372f3fb4c
%define shortcommit %(c=%{commit}; echo ${c:0:7})

%global genericname gdata

Summary:        A Java implementation of older Google Data (GData) Protocol
Name:           %{genericname}-java
Version:        2.2.1_alpha
Release:        1
License:        ASL 2.0
Group:          Development/Java
URL:            https://github.com/google/%{name}-client/
Source0:        https://github.com/google/%{name}-client/archive/%{commit}/%{name}-client-%{commit}.zip
Source1:        https://repo1.maven.org/maven2/com/google/gdata/core/1.47.1/core-1.47.1.pom
Patch0:         %{name}-client-c6202a55-remove_deprecated_modules.patch
Patch1:         %{name}-client-c6202a55-fix_annotation.patch
Patch2:         %{name}-client-c6202a55-fix_manifest.patch
BuildArch:      noarch

BuildRequires:  jpackage-utils
BuildRequires:  ant
BuildRequires:  aqute-bnd
BuildRequires:  google-oauth-java-client
BuildRequires:  google-http-java-client
BuildRequires:  guava
BuildRequires:  javamail
BuildRequires:  jsr-305
BuildRequires:  servlet3

%description
The Google data APIs ("GData" for short) provide a simple standard protocol
for reading and writing data on the web. GData combines common XML-based
syndication formats (Atom and RSS) with a feed-publishing system based on
the Atom publishing protocol, plus some extensions for handling queries.

Google also provides a set of client libraries for interacting with
GData-enabled services, in a variety of programming languages. Using these
libraries, you can construct GData requests, send them to a service, and
receive responses.

Several services currently support the GData API. A complete up-to-date
list along with respective documentation can be found on the GData site:
http://code.google.com/apis/gdata

%files -f .mfiles
%{_mavenpomdir}/*
%{_javadir}/%{genericname}/%{genericname}-*.jar
%doc README.md
%doc README-src.txt
%doc README-samples.txt
%doc RELEASE_NOTES.txt
%doc COPYING

#----------------------------------------------------------------------------

%package javadoc
Summary:  Javadoc for %{genericname}

%description javadoc
API documentation for %{genericname}.

%files javadoc
%{_javadocdir}/%{genericname}/*
%doc COPYING

#----------------------------------------------------------------------------

%prep
%setup -q -n %{name}-client-%{commit}
# Delete all prebuild JARs and libs
find . -name "*.jar" -delete
find . -name "*.class" -delete

# Apply all patches
%patch0 -p1 -b .modules
%patch1 -p1 -b .annotation
%patch2 -p1 -b .manifest

pushd java
rm -rf lib/* deps/* classes doc

properties=build-src/build.properties
for jars in \
  "servlet servlet" \
  "mail javamail/mail" \
  "activation jsr-305" \
  "guava guava" \
  "google-jsr305.jar jsr-305" \
  "google-oauth-client google-oauth-java-client"
do
  f=`echo $jars | gawk '{print $1;}'`
  g=`echo $jars | gawk '{print $2;}'`
  sed -i -e "/^${f}/s|=.*$|=`build-classpath ${g}`|" $properties
done
echo "" >> $properties
echo "google-http-client.jar=`build-classpath google-http-java-client`" >> $properties

for i in $(ls manifest/*.manifest); do
  sed -i '/class-path/I d' $i
  echo "Export-Package: $(grep '^Name' $i | sed -e 's|^Name: *||' -e 's|/|.|g' -e 's|.$||');version=\"%{version}\"" >> $i
done

mkdir bnd
for i in $(ls manifest/*.manifest); do
  b=${i//manifest/bnd}
  sed -e '/class-path/I d' -e '/Export-Package:/I d' -e '/Name:/I d' $i > $b
  grep '^Name' $i | sed -e 's|^Name: *|Bundle-SymbolicName: |' -e 's|/|.|g' -e 's|.$||' >> $b
  grep '^Specification-Title' $i | sed -e 's|^Specification-Title: *|Bundle-Name: |' >> $b
  grep '^Implementation-Title' $i | sed -e 's|^Implementation-Title: *|Bundle-Description: |' >> $b
  grep '^Specification-Version' $i | sed -e 's|^Specification-Version: *|Bundle-Version: |' >> $b
  echo "Export-Package: *" >> $b
done

# fix client.bnd
sed -i -e "s|com.google.gdata.client|com.google.gdata.data.extensions|g" bnd/client.bnd
echo "Import-Package: !com.google.gdata.data.extensions,*" >> bnd/client.bnd

popd

# pom.xml
cp %{SOURCE1} gdata-core-pom.xml

# Adjust the sources and tests path
%pom_xpath_inject "pom:project/pom:build" "
  <sourceDirectory>java/src/</sourceDirectory>
  <testSourceDirectory>java/src/</testSourceDirectory>" gdata-core-pom.xml

# Remove unuseful plugin
%pom_remove_plugin :maven-gpg-plugin gdata-core-pom.xml

%build
export CLASSPATH=$(build-classpath google-oauth-java-client google-http-java-client guava javamail/mail jsr-305)

pushd java
%ant -lib lib/%{genericname}-core-1.0.jar:lib/%{genericname}-client-1.0.jar -buildfile build-src.xml clean build

find src -name '*.java' |xargs javadoc -classpath \
  `build-classpath javamail google-oauth-java-client google-http-java-client guava jsr-305`:/etc/alternatives/java_sdk_openjdk/lib/tools.jar -d doc
popd

%install
#jars
pushd java
pushd lib
install -d %{buildroot}%{_javadir}/%{genericname}
install -m644 *.jar %{buildroot}%{_javadir}/%{genericname}
for i in `ls *.jar`; do
  x=`echo $i | tr -d [:digit:]`
  ln -s $i %{buildroot}%{_javadir}/%{genericname}/${x%%-\.\.jar}.jar
done
popd

# javadoc
install -d %{buildroot}%{_javadocdir}/%{genericname}
cp -rp doc/* %{buildroot}%{_javadocdir}/%{genericname}
popd

# pom dir
install -d -m 0755 %{buildroot}%{_mavenpomdir}

# pom
# Only gdata-core included for now, feel free to add more artifacts to pom file if you need
install -pm 0644 gdata-core-pom.xml %{buildroot}%{_mavenpomdir}/JPP.%{genericname}-%{genericname}-core.pom

# depmap
%add_maven_depmap JPP.%{genericname}-%{genericname}-core.pom %{genericname}/%{genericname}-core.jar

%changelog
* Tue Sep  4 2012 Mikolaj Izdebski <mizdebsk@redhat.com> - 1.45.0-5
- Install COPYING file with javadoc package
- Update to current packaging guidelines

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.45.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.45.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Wed Aug 03 2011 Marek Goldmann <mgoldman@redhat.com> - 1.45.0-2
- Added maven depmap for gdata-core

* Fri Jul 01 2011 Sandro Mathys <red at fedoraproject.org> - 1.45.0-1
- New upstream version 1.45.0
- Added Export-Package data to manifest files (OSGi)

* Wed Mar 16 2011 Alexander Kurtakov <akurtako@redhat.com> 1.41.2-3
- Build against servlet25.

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.41.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Jun 17 2010 Lubomir Rintel <lkundrak@v3.sk> - 1.41.2-1
- Rebase to later version, so that we include analytics api

* Fri Jul 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.28.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Tue Feb 24 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.28.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Dec 18 2008 Sandro Mathys <red at fedoraproject.org> - 1.28.0-1
- New version

* Thu Dec 18 2008 Sandro Mathys <red at fedoraproject.org> - 1.26.0-2
- The changes to the build.properties file are now applied with a for loop
and sed instead of a patch
- The paths to the 3rd-party libraries (i.e. currently only javamail.jar)
for the javadoc generation are now looked up with build-classpath instead of
being hardcoded

* Tue Dec 16 2008 Sandro Mathys <red at fedoraproject.org> - 1.26.0-1
- initial build (thanks Rudolf 'che' Kastl for the help)

<%inherit file="notify_base.mako" />

<%def name="content()">
<tr>
  <td style="border-collapse: collapse;">
    <h3 class="text-center" style="padding: 0;margin: 0;border: none;list-style: none;font-weight: 300;text-align: center;">Welcome to the GakuNin RDM!</h3>
  </td>
</tr>
<tr>
  <td style="border-collapse: collapse;">

Hello ${user.fullname},<br>
<br>
Thank you for verifying your account on GakuNin RDM, a free, open source service maintained by the National Institute of Informatics. Here are a few things you can do with GakuNin RDM:
<br>

% if storage_flag_is_active:
<h4>Select your storage location</h4>
Files can be stored in a location you specify from the available geographic regions for new projects. <a href="${domain}settings/account/?utm_source=notification&utm_medium=email&utm_campaign=welcome#updateDefaultStorageLocation">Set storage location.</a><br>
<br>
% endif

<h4>Store your files</h4>
Archive your materials, data, manuscripts, or anything else associated with your work during the research process or after it is complete. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019930613/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Learn how.</a><br>
<br>

<h4>Affiliate your projects with your institution</h4>
Associate your projects with your institution. They will be added to your institution's central commons, improving discoverability of your work and fostering collaboration.<br>
<br>

% if use_viewonlylinks:
<h4>Share your work</h4>
Keep your research materials and data private, make it accessible to specific others with view-only links, or make it publicly accessible. You have full control of what parts of your research are public and what remains private. <a href="https://openscience.zendesk.com/hc/en-us/articles/360018981414/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Explore privacy settings.</a><br>
<br>
% endif

<h4>Register your research</h4>
Create a permanent, time-stamped version of your projects and files.  Do this to preregister your design and analysis plan to conduct a confirmatory study, or archive your materials, data, and analysis scripts when publishing a report. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019930893/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Read about registrations.</a><br>
<br>

<h4>Make your work citable</h4>
Every project and file on the GakuNin RDM has a permanent unique identifier, and every registration can be assigned a DOI.  Citations for public projects are generated automatically so that visitors can give you credit for your research. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019931013/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Learn more.</a><br>
<br>

<h4>Measure your impact</h4>
You can monitor traffic to your public projects and downloads of your public files. <a href="https://openscience.zendesk.com/hc/en-us/articles/360019737874/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Discover analytics.</a><br>
<br>

<h4>Connect services that you use</h4>
GakuNin RDM integrates with GitHub, Dropbox, Google Drive, Box, Dataverse, figshare, Amazon S3, ownCloud, Bitbucket, GitLab, OneDrive, Mendeley, and Zotero. Link the services that you use to your GakuNin RDM projects so that all parts of your research are in one place <a href="https://openscience.zendesk.com/hc/en-us/categories/360001550973/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Learn about add-ons.</a><br>
<br>

<h4>Collaborate</h4>
Add your collaborators to have a shared environment for maintaining your research materials and data and never lose files again. <a href="https://openscience.zendesk.com/hc/en-us/categories/360001530674-Collaborating/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Start collaborating.</a><br>
<br>

Learn more about GakuNin RDM by reading the <a href="https://openscience.zendesk.com/hc/en-us/?utm_source=notification&utm_medium=email&utm_campaign=welcome">Guides</a>.<br>
<br>
Sincerely,<br>
<br>
The National Institute of Informatics Team<br>

  </td>
</tr>
</%def>
